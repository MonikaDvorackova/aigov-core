//! Deployment environment (`dev` | `staging` | `prod`) for policy selection and run labeling.
//!
//! # Source of truth
//! Authoritative semantics are documented in **[`docs/env-resolution.md`](../../docs/env-resolution.md)**
//! at the repository root. Rust and Python implement the same contract.
//!
//! # Resolution (process environment)
//! - Precedence: **`AIGOV_ENVIRONMENT`**, then **`AIGOV_ENV`**, then **`GOVAI_ENV`** (first non-empty wins).
//! - Parsing: [`parse_environment_value`] on the chosen value after trim.
//! - **Empty / unset / whitespace-only** → **`dev`**.
//! - **Invalid non-empty** → error at startup ([`resolve_from_env`]) or when validating a client field.
//!
//! # Evidence ingest
//! [`stamp_event_environment_for_ingest`] validates client claims against the server tier and rejects
//! mixed-environment runs. Legacy log lines may omit `environment`; new appends always stamp it.

use crate::schema::EvidenceEvent;
use std::fmt;

/// Tier this GovAI process enforces and stamps on evidence events.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GovaiEnvironment {
    Dev,
    Staging,
    Prod,
}

impl GovaiEnvironment {
    pub fn as_str(self) -> &'static str {
        match self {
            GovaiEnvironment::Dev => "dev",
            GovaiEnvironment::Staging => "staging",
            GovaiEnvironment::Prod => "prod",
        }
    }
}

impl fmt::Display for GovaiEnvironment {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

fn raw_from_env() -> String {
    for key in ["AIGOV_ENVIRONMENT", "AIGOV_ENV", "GOVAI_ENV"] {
        if let Ok(v) = std::env::var(key) {
            if !v.trim().is_empty() {
                return v;
            }
        }
    }
    String::new()
}

/// Parse a single env var value (trimmed). Empty → [`GovaiEnvironment::Dev`].
pub fn parse_environment_value(raw: &str) -> Result<GovaiEnvironment, String> {
    let t = raw.trim();
    if t.is_empty() {
        return Ok(GovaiEnvironment::Dev);
    }
    match t.to_ascii_lowercase().as_str() {
        "dev" | "development" | "local" => Ok(GovaiEnvironment::Dev),
        "staging" | "stage" => Ok(GovaiEnvironment::Staging),
        "prod" | "production" => Ok(GovaiEnvironment::Prod),
        other => Err(format!(
            "Invalid AIGOV_ENVIRONMENT={other:?} (expected dev, staging, or prod; see docs/env-resolution.md)"
        )),
    }
}

/// Resolve and validate deployment environment. Call once at process startup.
pub fn resolve_from_env() -> Result<GovaiEnvironment, String> {
    parse_environment_value(&raw_from_env())
}

/// Policy bundle id for this tier (distinct hashes per environment in `/bundle-hash`).
pub fn policy_version_for(env: GovaiEnvironment) -> &'static str {
    match env {
        GovaiEnvironment::Dev => "v0.5_dev",
        GovaiEnvironment::Staging => "v0.5_staging",
        GovaiEnvironment::Prod => "v0.5_prod",
    }
}

/// Consensus environment tag from the ledger, or `None` if all events omit it (legacy).
/// Returns `Err` if two distinct valid tags appear (corrupt / mixed ledger).
pub fn ledger_environment_consensus(
    events: &[EvidenceEvent],
) -> Result<Option<GovaiEnvironment>, String> {
    let mut acc: Option<GovaiEnvironment> = None;
    for e in events {
        if let Some(ref s) = e.environment {
            let t = s.trim();
            if t.is_empty() {
                continue;
            }
            let v = parse_environment_value(t)
                .map_err(|msg| format!("ledger parse error on event_id={}: {msg}", e.event_id))?;
            match acc {
                None => acc = Some(v),
                Some(known) if known == v => {}
                Some(known) => {
                    return Err(format!(
                        "ledger environment conflict for run: {} vs {}",
                        known.as_str(),
                        v.as_str()
                    ));
                }
            }
        }
    }
    Ok(acc)
}

/// Validate client claim, reject cross-tier runs, stamp [`EvidenceEvent::environment`].
pub fn stamp_event_environment_for_ingest(
    event: &mut EvidenceEvent,
    deployment: GovaiEnvironment,
    existing_same_run: &[EvidenceEvent],
) -> Result<(), String> {
    let canon = deployment.as_str();

    if let Some(claimed) = event.environment.take() {
        let t = claimed.trim();
        if !t.is_empty() {
            let parsed = parse_environment_value(t)?;
            if parsed.as_str() != canon {
                let show = claimed.clone();
                event.environment = Some(claimed);
                return Err(format!(
                    "policy_violation: event.environment={show:?} does not match server deployment {canon}"
                ));
            }
        }
    }

    for e in existing_same_run {
        if let Some(ref pe) = e.environment {
            let t = pe.trim();
            if t.is_empty() {
                continue;
            }
            let prev = parse_environment_value(t).map_err(|msg| {
                format!(
                    "policy_violation: log contains invalid environment={pe:?} on event_id={}: {msg}",
                    e.event_id
                )
            })?;
            if prev.as_str() != canon {
                return Err(format!(
                    "policy_violation: run_id {} already tagged environment={pe:?}; refusing {canon}",
                    event.run_id
                ));
            }
        }
    }

    event.environment = Some(canon.to_string());
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_empty_is_dev() {
        assert_eq!(parse_environment_value("").unwrap(), GovaiEnvironment::Dev);
        assert_eq!(
            parse_environment_value("   ").unwrap(),
            GovaiEnvironment::Dev
        );
    }

    #[test]
    fn parse_aliases() {
        for s in ["dev", "DEV", "development", "local", " Local "] {
            assert_eq!(
                parse_environment_value(s).unwrap(),
                GovaiEnvironment::Dev,
                "{s:?}"
            );
        }
        for s in ["staging", "stage", "STAGING"] {
            assert_eq!(
                parse_environment_value(s).unwrap(),
                GovaiEnvironment::Staging,
                "{s:?}"
            );
        }
        for s in ["prod", "production", "PROD"] {
            assert_eq!(
                parse_environment_value(s).unwrap(),
                GovaiEnvironment::Prod,
                "{s:?}"
            );
        }
    }

    #[test]
    fn parse_invalid_non_empty_fails() {
        assert!(parse_environment_value("prodd").is_err());
        assert!(parse_environment_value("stg").is_err());
        assert!(parse_environment_value("qa").is_err());
    }

    #[test]
    fn stamp_allows_legacy_existing_then_stamps() {
        let mut ev = EvidenceEvent {
            event_id: "e1".into(),
            event_type: "data_registered".into(),
            ts_utc: "t".into(),
            actor: "a".into(),
            system: "s".into(),
            run_id: "r1".into(),
            environment: None,
            payload: serde_json::json!({}),
        };
        stamp_event_environment_for_ingest(&mut ev, GovaiEnvironment::Dev, &[]).unwrap();
        assert_eq!(ev.environment.as_deref(), Some("dev"));
    }

    #[test]
    fn stamp_rejects_client_mismatch() {
        let mut ev = EvidenceEvent {
            event_id: "e1".into(),
            event_type: "data_registered".into(),
            ts_utc: "t".into(),
            actor: "a".into(),
            system: "s".into(),
            run_id: "r1".into(),
            environment: Some("prod".into()),
            payload: serde_json::json!({}),
        };
        let err =
            stamp_event_environment_for_ingest(&mut ev, GovaiEnvironment::Dev, &[]).unwrap_err();
        assert!(err.contains("does not match"));
    }

    #[test]
    fn stamp_rejects_mixed_run() {
        let existing = vec![EvidenceEvent {
            event_id: "e0".into(),
            event_type: "data_registered".into(),
            ts_utc: "t".into(),
            actor: "a".into(),
            system: "s".into(),
            run_id: "r1".into(),
            environment: Some("staging".into()),
            payload: serde_json::json!({}),
        }];
        let mut ev = EvidenceEvent {
            event_id: "e1".into(),
            event_type: "model_trained".into(),
            ts_utc: "t".into(),
            actor: "a".into(),
            system: "s".into(),
            run_id: "r1".into(),
            environment: None,
            payload: serde_json::json!({}),
        };
        let err = stamp_event_environment_for_ingest(&mut ev, GovaiEnvironment::Dev, &existing)
            .unwrap_err();
        assert!(err.contains("already tagged"));
    }

    #[test]
    fn ledger_consensus_none_for_legacy() {
        let ev = EvidenceEvent {
            event_id: "e1".into(),
            event_type: "data_registered".into(),
            ts_utc: "t".into(),
            actor: "a".into(),
            system: "s".into(),
            run_id: "r1".into(),
            environment: None,
            payload: serde_json::json!({}),
        };
        assert_eq!(ledger_environment_consensus(&[ev]).unwrap(), None);
    }

    #[test]
    fn ledger_consensus_conflict() {
        let a = EvidenceEvent {
            event_id: "e1".into(),
            event_type: "data_registered".into(),
            ts_utc: "t".into(),
            actor: "a".into(),
            system: "s".into(),
            run_id: "r1".into(),
            environment: Some("dev".into()),
            payload: serde_json::json!({}),
        };
        let b = EvidenceEvent {
            event_id: "e2".into(),
            event_type: "model_trained".into(),
            ts_utc: "t".into(),
            actor: "a".into(),
            system: "s".into(),
            run_id: "r1".into(),
            environment: Some("prod".into()),
            payload: serde_json::json!({}),
        };
        assert!(ledger_environment_consensus(&[a, b]).is_err());
    }
}

#[cfg(test)]
mod env_os_tests {
    use super::*;
    use std::sync::Mutex;

    static ENV_LOCK: Mutex<()> = Mutex::new(());

    fn clear_env_keys() {
        for k in ["AIGOV_ENVIRONMENT", "AIGOV_ENV", "GOVAI_ENV"] {
            std::env::remove_var(k);
        }
    }

    #[test]
    fn resolve_skips_whitespace_only_for_next_key() {
        let _g = ENV_LOCK.lock().unwrap();
        clear_env_keys();
        std::env::set_var("AIGOV_ENVIRONMENT", "   ");
        std::env::set_var("AIGOV_ENV", "staging");
        assert_eq!(resolve_from_env().unwrap(), GovaiEnvironment::Staging);
        clear_env_keys();
    }

    #[test]
    fn resolve_invalid_var_fails() {
        let _g = ENV_LOCK.lock().unwrap();
        clear_env_keys();
        std::env::set_var("AIGOV_ENVIRONMENT", "qa");
        assert!(resolve_from_env().is_err());
        clear_env_keys();
    }

    #[test]
    fn resolve_precedence_first_non_empty() {
        let _g = ENV_LOCK.lock().unwrap();
        clear_env_keys();
        std::env::set_var("AIGOV_ENVIRONMENT", "dev");
        std::env::set_var("AIGOV_ENV", "prod");
        assert_eq!(resolve_from_env().unwrap(), GovaiEnvironment::Dev);
        clear_env_keys();
    }
}
