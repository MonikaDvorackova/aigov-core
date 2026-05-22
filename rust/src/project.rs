//! Tenant/project isolation helpers: resolve tenant id and ledger path per request.

use crate::api_usage;
use crate::audit_api_key;
use crate::govai_environment::GovaiEnvironment;
use axum::http::HeaderMap;

const HDR: &str = "x-govai-project";

/// Reads `X-GovAI-Project`; empty or missing → `"default"`.
/// Single entry for billing / `GET /usage` tenant scope: header + bearer (see [`tenant_id_for_usage`]).
pub fn usage_tenant_id(headers: &HeaderMap) -> String {
    tenant_id_for_usage(headers, audit_api_key::raw_bearer_token(headers))
}

/// Stable *project label* for usage / quotas: `X-GovAI-Project` (if set), else API key fingerprint, else `default`.
pub fn tenant_id_for_usage(headers: &HeaderMap, bearer_token: Option<&str>) -> String {
    let raw = headers
        .get(HDR)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .trim();
    if !raw.is_empty() {
        return sanitize_project_segment(raw);
    }
    if let Some(t) = bearer_token {
        let t = t.trim();
        if !t.is_empty() {
            return api_usage::key_fingerprint(t);
        }
    }
    "default".to_string()
}

/// Canonical tenant id for tenant-isolated ledger access (env map only; prefer [`require_tenant_id_for_ledger_async`]).
pub fn require_tenant_id_for_ledger(
    headers: &HeaderMap,
    deployment_env: GovaiEnvironment,
) -> Result<String, String> {
    audit_api_key::require_tenant_id_from_api_key_for_ledger(headers, deployment_env)
}

/// Resolves ledger tenant from env API-key map or DB-issued self-service keys.
pub async fn require_tenant_id_for_ledger_async(
    pool: &crate::db::DbPool,
    headers: &HeaderMap,
    deployment_env: GovaiEnvironment,
) -> Result<String, String> {
    crate::tenant_api_keys::resolve_ledger_tenant_for_bearer(pool, headers, deployment_env).await
}

fn sanitize_project_segment(project_id: &str) -> String {
    let s: String = project_id
        .chars()
        .map(|c| match c {
            'a'..='z' | 'A'..='Z' | '0'..='9' | '-' | '_' => c,
            _ => '_',
        })
        .take(128)
        .collect();
    if s.is_empty() {
        "_".to_string()
    } else {
        s
    }
}

/// Deterministic tenant-scoped ledger path.
///
/// `ledger_base` is e.g. `audit_log.jsonl`. Always returns a tenant-specific `.jsonl` file.
pub fn resolve_ledger_path(ledger_base: &str, tenant_id: &str) -> String {
    let stem = ledger_base.strip_suffix(".jsonl").unwrap_or(ledger_base);
    let safe = sanitize_project_segment(tenant_id);
    let filename = format!("{}__{}.jsonl", stem, safe);

    // Optional base directory override for deployments and tests.
    // Applied only when `ledger_base` is a simple filename (no parent directory).
    let has_parent_dir = std::path::Path::new(ledger_base)
        .parent()
        .is_some_and(|p| !p.as_os_str().is_empty() && p != std::path::Path::new("."));
    if !has_parent_dir {
        if let Ok(dir) = std::env::var("GOVAI_LEDGER_DIR") {
            let dir = dir.trim();
            if !dir.is_empty() {
                return std::path::Path::new(dir)
                    .join(filename)
                    .to_string_lossy()
                    .to_string();
            }
        }
    }

    filename
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::HeaderValue;
    use std::sync::{Mutex, OnceLock};

    fn env_lock() -> &'static Mutex<()> {
        static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
        LOCK.get_or_init(|| Mutex::new(()))
    }

    fn ensure_test_key_map() {
        if crate::audit_api_key::api_key_tenant_map_is_initialized() {
            return;
        }
        std::env::set_var(
            "GOVAI_API_KEYS_JSON",
            r#"{ "mysecret": "team_1", "othersecret": "team_2" }"#,
        );
        // Ignore errors if another test raced to init first.
        let _ = crate::audit_api_key::init_api_key_tenant_map(GovaiEnvironment::Prod);
    }

    /// Bearer token + ledger tenant expected in `GOVAI_API_KEYS_JSON` (works when another test module initialized the map first).
    fn test_api_key_and_ledger_tenant() -> (&'static str, &'static str) {
        if crate::audit_api_key::env_tenant_map_contains_token("mysecret") {
            return ("mysecret", "team_1");
        }
        if crate::audit_api_key::env_tenant_map_contains_token("test-api-key") {
            return ("test-api-key", "team-alpha");
        }
        ensure_test_key_map();
        ("mysecret", "team_1")
    }

    #[test]
    fn usage_tenant_prefers_x_govai_project() {
        let mut h = HeaderMap::new();
        h.insert("x-govai-project", HeaderValue::from_static("team-alpha"));
        assert_eq!(usage_tenant_id(&h), "team-alpha");
    }

    #[test]
    fn usage_tenant_falls_back_to_key_fingerprint() {
        let mut h = HeaderMap::new();
        h.insert("Authorization", HeaderValue::from_static("Bearer test-api-key"));
        let tid = usage_tenant_id(&h);
        assert_ne!(tid, "default");
        assert_eq!(tid, crate::api_usage::key_fingerprint("test-api-key"));
    }

    #[test]
    fn usage_tenant_default_without_header_or_bearer() {
        let h = HeaderMap::new();
        assert_eq!(usage_tenant_id(&h), "default");
    }

    #[test]
    fn require_tenant_id_for_ledger_does_not_trust_x_govai_project_header() {
        let _g = env_lock().lock().unwrap();
        let mut h = HeaderMap::new();
        h.insert("x-govai-project", HeaderValue::from_static("team-alpha"));
        ensure_test_key_map();
        let err = require_tenant_id_for_ledger(&h, GovaiEnvironment::Prod).unwrap_err();
        assert_eq!(err, "missing_api_key");
    }

    #[test]
    fn require_tenant_id_for_ledger_uses_api_key_tenant_mapping() {
        let _g = env_lock().lock().unwrap();
        let (token, expected_tenant) = test_api_key_and_ledger_tenant();
        let mut h = HeaderMap::new();
        let auth = format!("Bearer {token}");
        h.insert("Authorization", HeaderValue::from_str(&auth).unwrap());
        let tid = require_tenant_id_for_ledger(&h, GovaiEnvironment::Prod).unwrap();
        assert_eq!(tid, expected_tenant);
    }

    #[test]
    fn require_tenant_id_for_ledger_missing_rejected_in_prod() {
        let _g = env_lock().lock().unwrap();
        ensure_test_key_map();
        let h = HeaderMap::new();
        let err = require_tenant_id_for_ledger(&h, GovaiEnvironment::Prod).unwrap_err();
        assert_eq!(err, "missing_api_key");
    }

    #[test]
    fn ledger_path_is_always_tenant_scoped() {
        assert_eq!(
            resolve_ledger_path("audit_log.jsonl", "default"),
            "audit_log__default.jsonl"
        );
    }
}
