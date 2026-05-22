//! File-backed policy knobs (`policy.<env>.json` / `policy.json`), merged with defaults.
//!
//! Resolution when **`AIGOV_POLICY_FILE`** is unset:
//! `policy.<env>.json` → `policy.json` → compile-time defaults, searched under:
//! - **`AIGOV_POLICY_DIR`** if set and non-empty (absolute or relative path), else
//! - the **process working directory** (`.`).
//!
//! If **`AIGOV_POLICY_FILE`** is set to a non-empty path, only that file is read.
//! Relative paths resolve from the process cwd.
//!
//! # Fail-fast vs dev fallback
//! - **`AIGOV_POLICY_STRICT=true`** (or `1` / `on` / `yes`): invalid or missing policy always aborts startup.
//! - **`GovaiEnvironment::Dev`** without strict policy: missing / unreadable / invalid JSON can fall back to
//!   compiled defaults (**not** allowed in staging or production).
//! Staging and production **always** require a resolvable valid policy file (env-specific file or `policy.json`
//! unless `AIGOV_POLICY_FILE` overrides).

use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::io::ErrorKind;
use std::path::{Path, PathBuf};

use crate::govai_environment::GovaiEnvironment;

pub const POLICY_REFUSE_MESSAGE: &str = "Invalid policy configuration: refusing to start";

fn policy_strict_from_env() -> bool {
    std::env::var("AIGOV_POLICY_STRICT")
        .ok()
        .map(|s| {
            matches!(
                s.trim().to_ascii_lowercase().as_str(),
                "1" | "true" | "on" | "yes"
            )
        })
        .unwrap_or(false)
}

fn allow_runtime_policy_fallback(deployment_env: GovaiEnvironment) -> bool {
    matches!(deployment_env, GovaiEnvironment::Dev) && !policy_strict_from_env()
}

#[cfg(test)]
pub(crate) mod test_sync {
    use std::sync::Mutex;
    /// Serializes tests that set/read `AIGOV_APPROVER_ALLOWLIST` (process-global).
    pub static APPROVER_ALLOWLIST_ENV_LOCK: Mutex<()> = Mutex::new(());
}

fn default_approver_allowlist() -> Vec<String> {
    vec!["compliance_officer".to_string(), "risk_officer".to_string()]
}

/// Runtime policy configuration loaded from JSON (or defaults).
#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
#[serde(default)]
pub struct PolicyConfig {
    /// **Affects:** `model_promoted` gate (human approval reference).
    ///
    /// - **true**: `model_promoted` requires `approved_human_event_id` and that it matches a prior
    ///   `human_approved` event with `decision=approve` for the same run + linkage fields.
    /// - **false**: promotion can proceed without any `human_approved` event reference (other gates may still apply).
    pub require_approval: bool,
    /// **Affects:** `model_trained` gate (data registration prerequisite).
    ///
    /// - **true**: `model_trained` requires a prior `data_registered` for the same `run_id`.
    /// - **false**: `model_trained` does not require prior `data_registered`.
    ///
    /// **Note:** This flag no longer “turns off all gating”. Promotion/approval gates are controlled by
    /// the explicit flags below (evaluation + risk review + human approval).
    pub block_if_missing_evidence: bool,
    /// **Affects:** `model_promoted` gate (evaluation prerequisite).
    ///
    /// - **true**: `model_promoted` requires a prior `evaluation_reported` with `passed=true` for the same run.
    /// - **false**: `model_promoted` does not require any evaluation event to have passed.
    pub require_passed_evaluation_for_promotion: bool,
    /// **Affects:** `human_approved` gate (risk review prerequisite).
    ///
    /// - **true**: `human_approved` requires a prior matching `risk_reviewed` with `decision=approve` for the same
    ///   run + linkage fields (assessment/risk/commitment/identifiers).
    /// - **false**: `human_approved` does not require prior risk review.
    pub require_risk_review_for_approval: bool,
    /// **Affects:** `model_promoted` gate (risk review prerequisite).
    ///
    /// - **true**: `model_promoted` requires a prior matching `risk_reviewed` with `decision=approve` for the same
    ///   run + linkage fields.
    /// - **false**: `model_promoted` does not require prior risk review.
    pub require_risk_review_for_promotion: bool,
    /// **Affects:** `human_approved` actor validation (`approver` field).
    ///
    /// - **true**: `human_approved.approver` must appear in the **effective allowlist**.
    /// - **false**: any non-empty `approver` is accepted (still requires required linkage fields).
    ///
    /// Effective allowlist is `AIGOV_APPROVER_ALLOWLIST` (if set and non-empty) else `approver_allowlist`.
    pub enforce_approver_allowlist: bool,
    /// **Affects:** `human_approved` actor allowlist contents.
    ///
    /// Only used when `enforce_approver_allowlist=true` *and* `AIGOV_APPROVER_ALLOWLIST` is not set.
    /// Values are normalized (trimmed + lowercased + de-duplicated) on load.
    #[serde(default = "default_approver_allowlist")]
    pub approver_allowlist: Vec<String>,
}

impl Default for PolicyConfig {
    fn default() -> Self {
        Self {
            require_approval: true,
            block_if_missing_evidence: true,
            require_passed_evaluation_for_promotion: true,
            require_risk_review_for_approval: true,
            require_risk_review_for_promotion: true,
            enforce_approver_allowlist: true,
            approver_allowlist: default_approver_allowlist(),
        }
    }
}

fn normalize_policy_config(cfg: &mut PolicyConfig) {
    let mut seen = HashSet::new();
    cfg.approver_allowlist = cfg
        .approver_allowlist
        .iter()
        .map(|s| s.trim().to_lowercase())
        .filter(|s| !s.is_empty())
        .filter(|s| seen.insert(s.clone()))
        .collect();
}

fn validate_policy_config(cfg: &PolicyConfig) -> Result<(), String> {
    if cfg.enforce_approver_allowlist && cfg.approver_allowlist.is_empty() {
        return Err(
            "enforce_approver_allowlist is true but approver_allowlist is empty after normalization"
                .to_string(),
        );
    }
    Ok(())
}

/// Allowlist used at ingest when [`PolicyConfig::enforce_approver_allowlist`] is true.
///
/// If `AIGOV_APPROVER_ALLOWLIST` is set and non-empty after trim, it overrides
/// [`PolicyConfig::approver_allowlist`] (comma-separated, same normalization as file entries).
pub fn effective_approver_allowlist(cfg: &PolicyConfig) -> Vec<String> {
    if let Ok(raw) = std::env::var("AIGOV_APPROVER_ALLOWLIST") {
        let trimmed = raw.trim();
        if !trimmed.is_empty() {
            let mut seen = HashSet::new();
            return trimmed
                .split(',')
                .map(|s| s.trim().to_lowercase())
                .filter(|s| !s.is_empty())
                .filter(|s| seen.insert(s.clone()))
                .collect();
        }
    }
    cfg.approver_allowlist.clone()
}

/// Where the effective [`PolicyConfig`] was resolved from (for `/status` and ops).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PolicySourceKind {
    OverrideFile,
    EnvFile,
    FallbackFile,
    Defaults,
}

/// Resolved file path label (relative to policy search dir when applicable, else absolute/display).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PolicySource {
    pub kind: PolicySourceKind,
    pub path: Option<String>,
}

/// Effective policy plus metadata from startup resolution.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResolvedPolicyConfig {
    pub config: PolicyConfig,
    pub source: PolicySource,
}

impl ResolvedPolicyConfig {
    /// Default [`PolicyConfig`] with [`PolicySourceKind::Defaults`] (e.g. tests / no policy files).
    pub fn all_defaults() -> Self {
        Self {
            config: PolicyConfig::default(),
            source: PolicySource {
                kind: PolicySourceKind::Defaults,
                path: None,
            },
        }
    }
}

fn policy_err(detail: impl std::fmt::Display) -> String {
    format!("{POLICY_REFUSE_MESSAGE} — {detail}")
}

/// Load policy for process startup. Fails closed when staging/prod (or **`AIGOV_POLICY_STRICT`**) forbids fallback.
pub fn load_for_deployment(
    deployment_env: GovaiEnvironment,
) -> Result<ResolvedPolicyConfig, String> {
    let allow_fallback = allow_runtime_policy_fallback(deployment_env);
    let override_path = std::env::var("AIGOV_POLICY_FILE")
        .ok()
        .filter(|s| !s.trim().is_empty());
    let search_base = std::env::var("AIGOV_POLICY_DIR")
        .ok()
        .filter(|s| !s.trim().is_empty())
        .map(|s| PathBuf::from(s.trim()))
        .unwrap_or_else(|| PathBuf::from("."));
    load_from_filesystem(
        deployment_env.as_str(),
        override_path,
        search_base.as_path(),
        allow_fallback,
    )
}

fn load_from_filesystem(
    env: &str,
    policy_file_override: Option<String>,
    search_dir: &Path,
    allow_fallback: bool,
) -> Result<ResolvedPolicyConfig, String> {
    let env_label = env.trim().to_ascii_lowercase();

    if let Some(raw) = policy_file_override {
        let p = PathBuf::from(raw.trim());
        return match read_policy_file(&p) {
            ReadOutcome::Ok(cfg) => {
                let src = PolicySource {
                    kind: PolicySourceKind::OverrideFile,
                    path: Some(p.display().to_string()),
                };
                log_loaded(&p, &env_label, &cfg);
                Ok(ResolvedPolicyConfig {
                    config: cfg,
                    source: src,
                })
            }
            ReadOutcome::Missing => {
                if !allow_fallback {
                    return Err(policy_err(format!(
                        "AIGOV_POLICY_FILE not found: {}",
                        p.display()
                    )));
                }
                eprintln!(
                    "[policy] warning: AIGOV_POLICY_FILE not found: {} (env={}) — using defaults",
                    p.display(),
                    env_label
                );
                let d = PolicyConfig::default();
                log_values(&d);
                Ok(ResolvedPolicyConfig {
                    config: d,
                    source: PolicySource {
                        kind: PolicySourceKind::Defaults,
                        path: None,
                    },
                })
            }
            ReadOutcome::Bad(msg) => {
                if !allow_fallback {
                    return Err(policy_err(msg));
                }
                eprintln!(
                    "[policy] warning: {} (env={}) — using defaults",
                    msg, env_label
                );
                let d = PolicyConfig::default();
                log_values(&d);
                Ok(ResolvedPolicyConfig {
                    config: d,
                    source: PolicySource {
                        kind: PolicySourceKind::Defaults,
                        path: None,
                    },
                })
            }
        };
    }

    let candidates = [
        (
            search_dir.join(format!("policy.{}.json", env_label)),
            PolicySourceKind::EnvFile,
        ),
        (
            search_dir.join("policy.json"),
            PolicySourceKind::FallbackFile,
        ),
    ];

    for (p, kind) in candidates {
        match read_policy_file(&p) {
            ReadOutcome::Ok(cfg) => {
                let path_label = path_for_metadata(&p, search_dir);
                log_loaded(&p, &env_label, &cfg);
                return Ok(ResolvedPolicyConfig {
                    config: cfg,
                    source: PolicySource {
                        kind,
                        path: Some(path_label),
                    },
                });
            }
            ReadOutcome::Missing => continue,
            ReadOutcome::Bad(msg) => {
                if !allow_fallback {
                    return Err(policy_err(msg));
                }
                eprintln!(
                    "[policy] warning: {} (env={}) — using defaults",
                    msg, env_label
                );
                let d = PolicyConfig::default();
                log_values(&d);
                return Ok(ResolvedPolicyConfig {
                    config: d,
                    source: PolicySource {
                        kind: PolicySourceKind::Defaults,
                        path: None,
                    },
                });
            }
        }
    }

    if !allow_fallback {
        return Err(policy_err(format!(
            "no policy file found for env={env_label}; expected policy.{env_label}.json or policy.json under {}",
            search_dir.display()
        )));
    }

    let d = PolicyConfig::default();
    eprintln!(
        "[policy] using defaults (env={}; no matching policy file)",
        env_label
    );
    log_values(&d);
    Ok(ResolvedPolicyConfig {
        config: d,
        source: PolicySource {
            kind: PolicySourceKind::Defaults,
            path: None,
        },
    })
}

fn path_for_metadata(path: &Path, search_dir: &Path) -> String {
    path.strip_prefix(search_dir)
        .ok()
        .map(|r| {
            let s = r.to_string_lossy();
            if s.is_empty() {
                path.file_name()
                    .map(|n| n.to_string_lossy().into_owned())
                    .unwrap_or_else(|| path.display().to_string())
            } else {
                s.into_owned()
            }
        })
        .unwrap_or_else(|| path.display().to_string())
}

enum ReadOutcome {
    Ok(PolicyConfig),
    Missing,
    Bad(String),
}

fn read_policy_file(path: &Path) -> ReadOutcome {
    match std::fs::read_to_string(path) {
        Ok(s) => match serde_json::from_str::<PolicyConfig>(&s) {
            Ok(mut c) => {
                normalize_policy_config(&mut c);
                if let Err(e) = validate_policy_config(&c) {
                    return ReadOutcome::Bad(format!(
                        "invalid policy in {}: {}",
                        path.display(),
                        e
                    ));
                }
                ReadOutcome::Ok(c)
            }
            Err(e) => ReadOutcome::Bad(format!("invalid JSON in {}: {}", path.display(), e)),
        },
        Err(e) if e.kind() == ErrorKind::NotFound => ReadOutcome::Missing,
        Err(e) => ReadOutcome::Bad(format!("could not read {}: {}", path.display(), e)),
    }
}

fn log_loaded(path: &Path, env_label: &str, cfg: &PolicyConfig) {
    eprintln!(
        "[policy] loaded from {} (env={})",
        path.display(),
        env_label
    );
    log_values(cfg);
}

fn log_values(cfg: &PolicyConfig) {
    eprintln!(
        "[policy] require_approval={}, block_if_missing_evidence={}, require_passed_evaluation_for_promotion={}, require_risk_review_for_approval={}, require_risk_review_for_promotion={}, enforce_approver_allowlist={}, approver_allowlist_len={}",
        cfg.require_approval,
        cfg.block_if_missing_evidence,
        cfg.require_passed_evaluation_for_promotion,
        cfg.require_risk_review_for_approval,
        cfg.require_risk_review_for_promotion,
        cfg.enforce_approver_allowlist,
        cfg.approver_allowlist.len()
    );
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    /// Production-like resolution: missing or invalid policy files are errors.
    fn load_strict(env: &str, dir: &Path) -> ResolvedPolicyConfig {
        load_from_filesystem(env, None, dir, false).unwrap()
    }

    /// Dev-only relaxed resolution (no strict flag): missing/invalid may fall back to defaults.
    fn load_dev_fallback(dir: &Path) -> ResolvedPolicyConfig {
        load_from_filesystem("dev", None, dir, true).unwrap()
    }

    #[test]
    fn loads_policy_dev_json_when_env_is_dev() {
        let dir = TempDir::new().unwrap();
        let body = r#"{"require_approval":false,"block_if_missing_evidence":false,"enforce_approver_allowlist":false}"#;
        fs::write(dir.path().join("policy.dev.json"), body).unwrap();
        let r = load_strict("dev", dir.path());
        assert_eq!(
            r.config,
            PolicyConfig {
                require_approval: false,
                block_if_missing_evidence: false,
                enforce_approver_allowlist: false,
                approver_allowlist: default_approver_allowlist(),
                require_passed_evaluation_for_promotion: true,
                require_risk_review_for_approval: true,
                require_risk_review_for_promotion: true,
            }
        );
        assert_eq!(r.source.kind, PolicySourceKind::EnvFile);
        assert_eq!(r.source.path.as_deref(), Some("policy.dev.json"));
    }

    #[test]
    fn falls_back_to_policy_json() {
        let dir = TempDir::new().unwrap();
        let body = r#"{"require_approval":false,"block_if_missing_evidence":true}"#;
        fs::write(dir.path().join("policy.json"), body).unwrap();
        let r = load_strict("staging", dir.path());
        assert_eq!(
            r.config,
            PolicyConfig {
                require_approval: false,
                block_if_missing_evidence: true,
                enforce_approver_allowlist: true,
                approver_allowlist: default_approver_allowlist(),
                require_passed_evaluation_for_promotion: true,
                require_risk_review_for_approval: true,
                require_risk_review_for_promotion: true,
            }
        );
        assert_eq!(r.source.kind, PolicySourceKind::FallbackFile);
        assert_eq!(r.source.path.as_deref(), Some("policy.json"));
    }

    #[test]
    fn prod_without_policy_file_errors_when_no_fallback() {
        let dir = TempDir::new().unwrap();
        let e = load_from_filesystem("prod", None, dir.path(), false).unwrap_err();
        assert!(e.contains(POLICY_REFUSE_MESSAGE));
    }

    #[test]
    fn dev_without_policy_file_uses_defaults_when_fallback_allowed() {
        let dir = TempDir::new().unwrap();
        let r = load_dev_fallback(dir.path());
        assert_eq!(r.config, PolicyConfig::default());
        assert_eq!(r.source.kind, PolicySourceKind::Defaults);
        assert_eq!(r.source.path, None);
    }

    #[test]
    fn invalid_json_uses_defaults_only_with_dev_fallback() {
        let dir = TempDir::new().unwrap();
        fs::write(dir.path().join("policy.dev.json"), "{ not json").unwrap();
        let r = load_dev_fallback(dir.path());
        assert_eq!(r.config, PolicyConfig::default());
        assert_eq!(r.source.kind, PolicySourceKind::Defaults);
        assert_eq!(r.source.path, None);
    }

    #[test]
    fn invalid_staging_json_errors_when_no_fallback() {
        let dir = TempDir::new().unwrap();
        fs::write(dir.path().join("policy.staging.json"), "{ not json").unwrap();
        let e = load_from_filesystem("staging", None, dir.path(), false).unwrap_err();
        assert!(e.contains(POLICY_REFUSE_MESSAGE));
    }

    #[test]
    fn env_specific_file_takes_precedence_over_policy_json() {
        let dir = TempDir::new().unwrap();
        fs::write(
            dir.path().join("policy.dev.json"),
            r#"{"require_approval":false,"block_if_missing_evidence":false,"enforce_approver_allowlist":false}"#,
        )
        .unwrap();
        fs::write(
            dir.path().join("policy.json"),
            r#"{"require_approval":true,"block_if_missing_evidence":true}"#,
        )
        .unwrap();
        let r = load_strict("dev", dir.path());
        assert_eq!(
            r.config,
            PolicyConfig {
                require_approval: false,
                block_if_missing_evidence: false,
                enforce_approver_allowlist: false,
                approver_allowlist: default_approver_allowlist(),
                require_passed_evaluation_for_promotion: true,
                require_risk_review_for_approval: true,
                require_risk_review_for_promotion: true,
            }
        );
        assert_eq!(r.source.kind, PolicySourceKind::EnvFile);
    }

    #[test]
    fn aigov_policy_file_override_in_search_dir() {
        let dir = TempDir::new().unwrap();
        let custom = dir.path().join("custom.json");
        fs::write(
            &custom,
            r#"{"require_approval":false,"block_if_missing_evidence":true}"#,
        )
        .unwrap();
        let r = load_from_filesystem(
            "prod",
            Some(custom.to_string_lossy().into_owned()),
            dir.path(),
            false,
        )
        .unwrap();
        assert_eq!(
            r.config,
            PolicyConfig {
                require_approval: false,
                block_if_missing_evidence: true,
                enforce_approver_allowlist: true,
                approver_allowlist: default_approver_allowlist(),
                require_passed_evaluation_for_promotion: true,
                require_risk_review_for_approval: true,
                require_risk_review_for_promotion: true,
            }
        );
        assert_eq!(r.source.kind, PolicySourceKind::OverrideFile);
        assert!(r.source.path.as_ref().is_some());
    }

    #[test]
    fn load_for_deployment_honors_aigov_policy_dir() {
        use std::sync::Mutex;
        static DIR_LOCK: Mutex<()> = Mutex::new(());
        let _g = DIR_LOCK.lock().unwrap();
        let orig_cwd = std::env::current_dir().unwrap();
        let policies = TempDir::new().unwrap();
        fs::write(
            policies.path().join("policy.staging.json"),
            r#"{"require_approval":true,"block_if_missing_evidence":true,"enforce_approver_allowlist":false}"#,
        )
        .unwrap();
        let empty_cwd = TempDir::new().unwrap();
        std::env::remove_var("AIGOV_POLICY_FILE");
        std::env::remove_var("AIGOV_POLICY_STRICT");
        std::env::set_var(
            "AIGOV_POLICY_DIR",
            policies.path().to_string_lossy().as_ref(),
        );
        std::env::set_current_dir(empty_cwd.path()).unwrap();
        let r = super::load_for_deployment(GovaiEnvironment::Staging).unwrap();
        assert!(!r.config.enforce_approver_allowlist);
        assert_eq!(r.source.kind, PolicySourceKind::EnvFile);
        assert_eq!(r.source.path.as_deref(), Some("policy.staging.json"));
        std::env::remove_var("AIGOV_POLICY_DIR");
        std::env::set_current_dir(orig_cwd).unwrap();
    }

    #[test]
    fn effective_allowlist_env_override() {
        let _g = test_sync::APPROVER_ALLOWLIST_ENV_LOCK.lock().unwrap();
        let mut cfg = PolicyConfig::default();
        cfg.approver_allowlist = vec!["from_file".to_string()];
        std::env::set_var("AIGOV_APPROVER_ALLOWLIST", "from_env,From_Env");
        let eff = effective_approver_allowlist(&cfg);
        assert_eq!(eff, vec!["from_env"]);
        std::env::remove_var("AIGOV_APPROVER_ALLOWLIST");
    }

    #[test]
    fn invalid_policy_empty_allowlist_with_enforce_errors_without_fallback() {
        let dir = TempDir::new().unwrap();
        fs::write(
            dir.path().join("policy.prod.json"),
            r#"{"enforce_approver_allowlist":true,"approver_allowlist":[]}"#,
        )
        .unwrap();
        let e = load_from_filesystem("prod", None, dir.path(), false).unwrap_err();
        assert!(e.contains(POLICY_REFUSE_MESSAGE));
    }

    #[test]
    fn invalid_policy_empty_allowlist_dev_fallback_still_defaults() {
        let dir = TempDir::new().unwrap();
        fs::write(
            dir.path().join("policy.dev.json"),
            r#"{"enforce_approver_allowlist":true,"approver_allowlist":[]}"#,
        )
        .unwrap();
        let r = load_dev_fallback(dir.path());
        assert_eq!(r.config, PolicyConfig::default());
        assert_eq!(r.source.kind, PolicySourceKind::Defaults);
    }

    #[test]
    fn empty_object_json_uses_all_defaults_including_allowlist() {
        let dir = TempDir::new().unwrap();
        fs::write(dir.path().join("policy.dev.json"), "{}").unwrap();
        let r = load_strict("dev", dir.path());
        assert_eq!(r.config, PolicyConfig::default());
        assert_eq!(r.source.kind, PolicySourceKind::EnvFile);
    }

    #[test]
    fn custom_allowlist_normalized() {
        let dir = TempDir::new().unwrap();
        fs::write(
            dir.path().join("policy.staging.json"),
            r#"{"enforce_approver_allowlist":true,"approver_allowlist":[" Lead ", "lead"]}"#,
        )
        .unwrap();
        let r = load_strict("staging", dir.path());
        assert_eq!(r.config.approver_allowlist, vec!["lead"]);
        assert_eq!(r.source.kind, PolicySourceKind::EnvFile);
    }

    #[test]
    fn partial_policy_json_defaults_new_enforcement_flags() {
        let dir = TempDir::new().unwrap();
        fs::write(
            dir.path().join("policy.dev.json"),
            r#"{"require_approval":false}"#,
        )
        .unwrap();
        let r = load_strict("dev", dir.path());
        assert!(!r.config.require_approval);
        assert!(r.config.require_passed_evaluation_for_promotion);
        assert!(r.config.require_risk_review_for_approval);
        assert!(r.config.require_risk_review_for_promotion);
    }

    #[test]
    fn load_for_deployment_strict_env_rejects_missing_file_even_on_dev() {
        use std::sync::Mutex;
        static ENV_LOCK: Mutex<()> = Mutex::new(());
        let _g = ENV_LOCK.lock().unwrap();
        let dir = TempDir::new().unwrap();
        std::env::remove_var("AIGOV_POLICY_FILE");
        std::env::set_var("AIGOV_POLICY_DIR", dir.path().to_string_lossy().as_ref());
        std::env::set_var("AIGOV_POLICY_STRICT", "true");
        let e = super::load_for_deployment(GovaiEnvironment::Dev).unwrap_err();
        assert!(e.contains(POLICY_REFUSE_MESSAGE));
        std::env::remove_var("AIGOV_POLICY_STRICT");
        std::env::remove_var("AIGOV_POLICY_DIR");
    }
}
