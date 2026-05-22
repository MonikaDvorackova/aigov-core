//! Shared-secret gate for core audit HTTP routes (`GOVAI_API_KEYS`).
//! Optional per-key request caps: `key:limit` entries and/or `GOVAI_API_KEY_DEFAULT_LIMIT`.
//! Usage (POST /evidence, GET /compliance-summary) is tracked in `api_usage` via
//! [`UsageChannel::EvidenceIngest`] / [`UsageChannel::ComplianceSummaryRead`].
//! `request_count` is still incremented (legacy); split columns are preferred for new diagnostics.
//! Billable run/event enforcement is in [`crate::metering`] when `GOVAI_METERING=on`.
//!
//! ## Operator contract
//!
//! Hosted API keys must be provisioned in **two** server-side env vars (and they must agree):
//!
//! 1. `GOVAI_API_KEYS`        — comma-separated bearer allowlist (with optional `key:limit`).
//!    Required for any audit route to authenticate (HTTP 401 INVALID_API_KEY otherwise).
//! 2. `GOVAI_API_KEYS_JSON`   — JSON object mapping `{"<api_key>": "<ledger_tenant_id>"}`.
//!    Server-controlled ledger tenant isolation (NEVER use `X-GovAI-Project` for this).
//!
//! [`validate_api_key_allowlist_consistency`] is invoked at startup by `lib::run` to
//! fail-fast in staging/prod if any key in `GOVAI_API_KEYS_JSON` is missing from
//! `GOVAI_API_KEYS` (a common operator footgun that yields HTTP 401 INVALID_API_KEY).

use crate::api_usage::{self, key_fingerprint, ApiUsageState, UsageChannel};
use crate::db::DbPool;
use crate::govai_environment::GovaiEnvironment;

use axum::extract::{Request, State};
use axum::http::{header, HeaderMap, Method, StatusCode};
use axum::middleware::Next;
use axum::response::{IntoResponse, Response};
use std::collections::{HashMap, HashSet};
use std::sync::{Arc, RwLock};

use crate::api_error::{api_error, api_error_with};
use once_cell::sync::OnceCell;

static API_KEY_TENANT_MAP: OnceCell<Arc<HashMap<String, String>>> = OnceCell::new();
static HOSTED_KEY_TENANT_BY_HASH: OnceCell<Arc<RwLock<HashMap<String, String>>>> = OnceCell::new();
static RUNTIME_API_KEY_TENANT_MAP: OnceCell<RwLock<HashMap<String, String>>> = OnceCell::new();

fn runtime_tenant_map() -> &'static RwLock<HashMap<String, String>> {
    RUNTIME_API_KEY_TENANT_MAP.get_or_init(|| RwLock::new(HashMap::new()))
}

/// Hosted self-service (`GOVAI_HOSTED_SELF_SERVICE=on`): DB-issued keys resolve by bearer hash.
pub fn hosted_self_service_enabled() -> bool {
    matches!(
        std::env::var("GOVAI_HOSTED_SELF_SERVICE")
            .map(|s| s.trim().to_ascii_lowercase())
            .unwrap_or_default()
            .as_str(),
        "1" | "true" | "yes" | "on"
    )
}

pub fn register_hosted_key_hash(key_hash: &str, ledger_tenant_id: &str) {
    if let Some(cell) = HOSTED_KEY_TENANT_BY_HASH.get() {
        if let Ok(mut guard) = cell.write() {
            guard.insert(key_hash.to_string(), ledger_tenant_id.to_string());
        }
    }
}

fn ensure_hosted_hash_map() {
    let _ = HOSTED_KEY_TENANT_BY_HASH.get_or_init(|| Arc::new(RwLock::new(HashMap::new())));
}

/// Register a provisioned API key in memory for ledger tenant resolution (process lifetime).
pub fn register_runtime_api_key(plaintext: &str, ledger_tenant_id: &str) -> Result<(), String> {
    let k = plaintext.trim();
    let v = ledger_tenant_id.trim();

    if k.is_empty() || v.is_empty() {
        return Err("register_runtime_api_key: empty key or tenant".to_string());
    }

    runtime_tenant_map()
        .write()
        .map_err(|e| format!("runtime api key map lock poisoned: {e}"))?
        .insert(k.to_string(), v.to_string());

    Ok(())
}

/// Resolve ledger tenant from env JSON map, hosted hash map, or runtime plaintext map.
pub fn resolve_ledger_tenant_id_for_bearer(token: &str) -> Option<String> {
    if token.is_empty() {
        return None;
    }
    if let Some(map) = API_KEY_TENANT_MAP.get() {
        if let Some(t) = map.get(token) {
            return Some(t.clone());
        }
    }
    if let Some(cell) = HOSTED_KEY_TENANT_BY_HASH.get() {
        let fp = key_fingerprint(token);
        if let Ok(guard) = cell.read() {
            if let Some(tenant_id) = guard.get(&fp) {
                return Some(tenant_id.clone());
            }
        }
    }

    runtime_tenant_map()
        .read()
        .ok()
        .and_then(|guard| guard.get(token).cloned())
}

pub fn api_key_tenant_map_is_initialized() -> bool {
    API_KEY_TENANT_MAP.get().is_some()
}

/// True when the bearer token appears in `GOVAI_API_KEYS_JSON` (env map).
pub fn env_tenant_map_contains_token(token: &str) -> bool {
    API_KEY_TENANT_MAP
        .get()
        .map(|m| m.contains_key(token))
        .unwrap_or(false)
}

/// True when the bearer token appears in `GOVAI_API_KEYS` allowlist.
pub fn env_allowlist_contains_token(token: &str) -> bool {
    AuditApiKeyConfig::from_env()
        .keys
        .as_ref()
        .map(|m| m.contains_key(token))
        .unwrap_or(false)
}

#[derive(Clone)]
pub struct AuditKeyGateState {
    pub cfg: AuditApiKeyConfig,
    pub usage: ApiUsageState,
    pub pool: DbPool,
    pub deployment_env: GovaiEnvironment,
}

/// Initialize `GOVAI_API_KEYS_JSON` (api_key -> tenant_id) mapping once at startup.
///
/// - **Dev**: missing/empty config is allowed (ledger tenant defaults to `"default"`).
/// - **Staging/Prod**: missing/invalid/empty config fails startup.
pub fn init_api_key_tenant_map(deployment_env: GovaiEnvironment) -> Result<(), String> {
    let raw = std::env::var("GOVAI_API_KEYS_JSON").ok();
    let raw = raw.as_deref().unwrap_or("").trim();

    ensure_hosted_hash_map();

    if raw.is_empty() {
        return match deployment_env {
            GovaiEnvironment::Dev => {
                let _ = API_KEY_TENANT_MAP.set(Arc::new(HashMap::new()));
                Ok(())
            }
            GovaiEnvironment::Staging | GovaiEnvironment::Prod => {
                if hosted_self_service_enabled() {
                    let _ = API_KEY_TENANT_MAP.set(Arc::new(HashMap::new()));
                    Ok(())
                } else {
                    API_KEY_TENANT_MAP
                        .set(Arc::new(HashMap::new()))
                        .map_err(|_| {
                            "GOVAI_API_KEYS_JSON was initialized more than once".to_string()
                        })?;
                    Ok(())
                }
            }
        };
    }

    let parsed: HashMap<String, String> = serde_json::from_str(raw).map_err(|e| {
        format!(
            "Invalid GOVAI_API_KEYS_JSON (expected JSON object mapping api_key -> tenant_id): {e}"
        )
    })?;

    let mut cleaned: HashMap<String, String> = HashMap::new();
    for (k, v) in parsed.into_iter() {
        let k = k.trim().to_string();
        let v = v.trim().to_string();
        if k.is_empty() || v.is_empty() {
            continue;
        }
        cleaned.insert(k, v);
    }

    if cleaned.is_empty() {
        return match deployment_env {
            GovaiEnvironment::Dev => Ok(()),
            GovaiEnvironment::Staging | GovaiEnvironment::Prod => Err(
                "GOVAI_API_KEYS_JSON must contain at least one api_key -> tenant_id entry"
                    .to_string(),
            ),
        };
    }

    API_KEY_TENANT_MAP
        .set(Arc::new(cleaned))
        .map_err(|_| "GOVAI_API_KEYS_JSON was initialized more than once".to_string())?;
    ensure_hosted_hash_map();
    Ok(())
}

/// Server-controlled tenant id for the tenant-isolated ledger.
///
/// Tenant identity is derived **only** from the API key (never from headers like `x-govai-project`).
pub fn require_tenant_id_from_api_key_for_ledger(
    headers: &HeaderMap,
    deployment_env: GovaiEnvironment,
) -> Result<String, String> {
    let token = match raw_bearer_token(headers) {
        Some(t) if !t.is_empty() => t,
        _ => {
            return match deployment_env {
                GovaiEnvironment::Dev if !hosted_self_service_enabled() => {
                    Ok("default".to_string())
                }
                _ => Err("missing_api_key".to_string()),
            };
        }
    };

    if let Some(tenant_id) = resolve_ledger_tenant_id_for_bearer(token) {
        return Ok(tenant_id);
    }

    let env_map_empty = API_KEY_TENANT_MAP
        .get()
        .map(|tenant_map| tenant_map.is_empty())
        .unwrap_or(true);

    match deployment_env {
        GovaiEnvironment::Dev if !hosted_self_service_enabled() && env_map_empty => {
            Ok("default".to_string())
        }
        GovaiEnvironment::Dev => Err("unknown_api_key".to_string()),
        GovaiEnvironment::Staging | GovaiEnvironment::Prod => {
            if API_KEY_TENANT_MAP.get().is_some() || hosted_self_service_enabled() {
                Err("unknown_api_key".to_string())
            } else {
                Err(
                    "GOVAI_API_KEYS_JSON is required in staging/prod (JSON object mapping api_key -> tenant_id)"
                        .to_string(),
                )
            }
        }
    }
}

#[derive(Clone)]
pub struct AuditApiKeyConfig {
    /// When `None`, authentication is disabled (legacy local behavior).
    /// Key = raw bearer token; value = max billable/tracked requests for that key (`None` = unlimited, still counted).
    pub keys: Option<Arc<HashMap<String, Option<u64>>>>,
}

/// One comma-separated entry: `rawsecret` or `rawsecret:max_requests` (per-key cap).
/// Optional `GOVAI_API_KEY_DEFAULT_LIMIT` applies to entries without `:number`.
impl AuditApiKeyConfig {
    pub fn from_env() -> Self {
        let default_cap = std::env::var("GOVAI_API_KEY_DEFAULT_LIMIT")
            .ok()
            .and_then(|s| s.parse::<u64>().ok());
        let Ok(raw) = std::env::var("GOVAI_API_KEYS") else {
            return Self { keys: None };
        };
        let raw = raw.trim();
        if raw.is_empty() {
            return Self { keys: None };
        }
        let mut m: HashMap<String, Option<u64>> = HashMap::new();
        for part in raw.split(',') {
            let (k, mut cap) = parse_key_entry(part);
            if k.is_empty() {
                continue;
            }
            if cap.is_none() {
                cap = default_cap;
            }
            m.insert(k, cap);
        }
        if m.is_empty() {
            Self { keys: None }
        } else {
            Self {
                keys: Some(Arc::new(m)),
            }
        }
    }
}

fn parse_key_entry(part: &str) -> (String, Option<u64>) {
    let s = part.trim();
    if s.is_empty() {
        return (String::new(), None);
    }
    if let Some(i) = s.rfind(':') {
        if let Ok(n) = s[i + 1..].trim().parse::<u64>() {
            let k = s[..i].trim();
            if !k.is_empty() {
                return (k.to_string(), Some(n));
            }
        }
    }
    (s.to_string(), None)
}

/// Parse a `GOVAI_API_KEYS` value (comma-separated, optional `key:limit`) into the
/// set of bare bearer tokens. Empty / unset → empty set.
pub fn parse_api_keys_allowlist(raw: &str) -> HashSet<String> {
    raw.split(',')
        .filter_map(|part| {
            let (k, _cap) = parse_key_entry(part);
            if k.is_empty() {
                None
            } else {
                Some(k)
            }
        })
        .collect()
}

/// Parse `GOVAI_API_KEYS_JSON` into a `HashMap<api_key, tenant_id>`. Returns `Ok(empty)`
/// when the env var is missing or whitespace-only. Returns `Err` only when JSON is invalid.
pub fn parse_api_key_tenant_map_from_env_value(
    raw: &str,
) -> Result<HashMap<String, String>, String> {
    let raw = raw.trim();
    if raw.is_empty() {
        return Ok(HashMap::new());
    }
    let parsed: HashMap<String, String> = serde_json::from_str(raw).map_err(|e| {
        format!(
            "Invalid GOVAI_API_KEYS_JSON (expected JSON object mapping api_key -> tenant_id): {e}"
        )
    })?;
    let mut cleaned = HashMap::new();
    for (k, v) in parsed.into_iter() {
        let k = k.trim().to_string();
        let v = v.trim().to_string();
        if !k.is_empty() && !v.is_empty() {
            cleaned.insert(k, v);
        }
    }
    Ok(cleaned)
}

/// Diagnostic for staging/prod operators: every key declared in `GOVAI_API_KEYS_JSON`
/// (the ledger-tenant mapping) must also be present in `GOVAI_API_KEYS` (the bearer
/// allowlist). Otherwise audit routes return HTTP 401 INVALID_API_KEY even though the
/// tenant mapping is "valid" — a confusing two-env-var footgun in production.
///
/// - **Dev**: returns `Ok` even if inconsistent (we already log a warning).
/// - **Staging/Prod**: returns `Err` listing the orphan keys (by sha256 fingerprint,
///   never raw) so the process fails fast with a clear, redaction-safe message.
pub fn validate_api_key_allowlist_consistency(
    deployment_env: GovaiEnvironment,
) -> Result<(), String> {
    let json_raw = std::env::var("GOVAI_API_KEYS_JSON").unwrap_or_default();
    let allowlist_raw = std::env::var("GOVAI_API_KEYS").unwrap_or_default();
    let json_map = parse_api_key_tenant_map_from_env_value(&json_raw)?;
    let allowlist = parse_api_keys_allowlist(&allowlist_raw);

    if json_map.is_empty() {
        return Ok(());
    }

    let orphans: Vec<String> = json_map
        .keys()
        .filter(|k| !allowlist.contains(*k))
        .map(|k| key_fingerprint(k))
        .collect();

    if orphans.is_empty() {
        return Ok(());
    }

    let summary = format!(
        "GOVAI_API_KEYS_JSON contains {} key(s) not present in GOVAI_API_KEYS \
         (sha256 fingerprints: {}). Audit routes will return HTTP 401 INVALID_API_KEY \
         for these keys until both env vars include them. Never log raw API keys.",
        orphans.len(),
        orphans.join(",")
    );

    match deployment_env {
        GovaiEnvironment::Dev => {
            eprintln!("warning: {summary}");
            Ok(())
        }
        GovaiEnvironment::Staging | GovaiEnvironment::Prod => Err(summary),
    }
}

/// Emit a redaction-safe diagnostic line on auth failure. Never logs the raw bearer
/// token; logs only the sha256 fingerprint and whether each env var is configured.
fn log_auth_failure_diagnostic(token: &str, code: &str, method: &Method, path: &str) {
    let fp = if token.is_empty() {
        String::from("<absent>")
    } else {
        key_fingerprint(token)
    };
    let keys_configured = std::env::var("GOVAI_API_KEYS")
        .ok()
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let json_configured = std::env::var("GOVAI_API_KEYS_JSON")
        .ok()
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    eprintln!(
        "auth_failure code={code} method={method} path={path} key_sha256_fingerprint={fp} \
         govai_api_keys_configured={keys_configured} govai_api_keys_json_configured={json_configured}"
    );
    let rk = crate::http_observability::route_metric_key(method, path);
    crate::ops_log::auth_failure_category(code, method.as_str(), &rk);
}

/// Raw bearer secret for tenant resolution (same parsing as the API key gate).
pub fn raw_bearer_token(headers: &HeaderMap) -> Option<&str> {
    let auth = headers
        .get(header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    let t = bearer_token(auth);
    if t.is_empty() {
        None
    } else {
        Some(t)
    }
}

fn bearer_token(authorization: &str) -> &str {
    let auth = authorization.trim();
    const PREFIX: &str = "Bearer ";
    if auth.len() >= PREFIX.len() && auth[..PREFIX.len()].eq_ignore_ascii_case(PREFIX) {
        auth[PREFIX.len()..].trim()
    } else {
        ""
    }
}

fn is_usage_routed_path(method: &Method, path: &str) -> bool {
    (path == "/evidence" && method == Method::POST)
        || (path == "/compliance-summary" && method == Method::GET)
        || (path == "/decision/evaluate" && method == Method::POST)
}

pub async fn gate_audit_routes_with_state(
    State(st): State<AuditKeyGateState>,
    mut request: Request,
    next: Next,
) -> Response {
    let cfg = st.cfg.clone();
    let usage = st.usage.clone();
    let pool = st.pool.clone();
    let deployment_env = st.deployment_env;

    let token = request
        .headers()
        .get(header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .map(bearer_token)
        .unwrap_or("")
        .to_string();

    let req_method = request.method().clone();
    let req_path = request.uri().path().to_string();

    let map_initialized = api_key_tenant_map_is_initialized();
    let keys_configured = cfg.keys.is_some();
    let hosted_self_service = hosted_self_service_enabled();

    // Primary allowlist: env JSON map, configured API keys, and/or hosted DB-issued keys by hash lookup.
    if map_initialized || keys_configured || hosted_self_service {
        if token.is_empty() {
            log_auth_failure_diagnostic(&token, "MISSING_API_KEY", &req_method, &req_path);
            return api_error(
                StatusCode::UNAUTHORIZED,
                "MISSING_API_KEY",
                "Missing API key.",
                "Provide `Authorization: Bearer <api_key>`.",
                None,
            )
            .into_response();
        }
        if let Some(key_map) = &cfg.keys {
            if !key_map.contains_key(&token) {
                log_auth_failure_diagnostic(&token, "INVALID_API_KEY", &req_method, &req_path);
                return api_error(
                    StatusCode::UNAUTHORIZED,
                    "INVALID_API_KEY",
                    "Invalid API key.",
                    "Verify you are using the correct GovAI API key and not a JWT. If you rotated keys, update your integration and retry.",
                    None,
                )
                .into_response();
            }
        }
        if resolve_ledger_tenant_id_for_bearer(&token).is_none()
            && !crate::tenant_api_keys::bearer_token_is_authorized(&pool, &token, deployment_env)
                .await
        {
            log_auth_failure_diagnostic(&token, "INVALID_API_KEY", &req_method, &req_path);
            return api_error(
                StatusCode::UNAUTHORIZED,
                "INVALID_API_KEY",
                "Invalid API key.",
                "Verify you're using the correct GovAI API key (and not a JWT). If you rotated keys, update your integration and retry.",
                None,
            )
            .into_response();
        }

        if let Ok(tid) = crate::tenant_api_keys::resolve_ledger_tenant_for_bearer(
            &pool,
            request.headers(),
            deployment_env,
        )
        .await
        {
            request.extensions_mut().insert(ResolvedLedgerTenant(tid));
        }

        if let Some(key_map) = &cfg.keys {
            // Optional per-key usage caps: when configured, require a valid API key.
            if token.is_empty() {
                log_auth_failure_diagnostic(&token, "MISSING_API_KEY", &req_method, &req_path);
                return api_error(
                    StatusCode::UNAUTHORIZED,
                    "MISSING_API_KEY",
                    "Missing API key.",
                    "Provide `Authorization: Bearer <api_key>`.",
                    None,
                )
                .into_response();
            }

            let hosted_ok = resolve_ledger_tenant_id_for_bearer(&token).is_some();
            let database_ok =
                crate::tenant_api_keys::bearer_token_is_authorized(&pool, &token, deployment_env)
                    .await;

            if !hosted_ok && !database_ok && !key_map.contains_key(&token) {
                log_auth_failure_diagnostic(&token, "INVALID_API_KEY", &req_method, &req_path);
                return api_error(
                    StatusCode::UNAUTHORIZED,
                    "INVALID_API_KEY",
                    "Invalid API key.",
                    "Verify you are using the correct GovAI API key and not a JWT. If you rotated keys, update your integration and retry.",
                    None,
                )
                .into_response();
            }
        }
    }

    if let Some(key_map) = &cfg.keys {
        let cap = key_map.get(token.as_str()).copied().flatten();
        if is_usage_routed_path(request.method(), request.uri().path()) {
            let ch = if request.method() == Method::POST && request.uri().path() == "/evidence" {
                UsageChannel::EvidenceIngest
            } else {
                UsageChannel::ComplianceSummaryRead
            };

            if let Err(e) = usage.try_increment(&token, cap, ch).await {
                return match e {
                    api_usage::UsageError::QuotaExceeded { limit, current } => api_error_with(
                        StatusCode::TOO_MANY_REQUESTS,
                        "USAGE_LIMIT_EXCEEDED",
                        "This API key has exceeded its request limit.",
                        "Wait for the quota reset or use an API key with a higher limit.",
                        Some(serde_json::json!({ "limit": limit, "used": current })),
                        Some(serde_json::json!({
                            "metering": "n/a",
                            "count_kind": "api_key_total_requests",
                            "operation": match ch {
                                UsageChannel::EvidenceIngest => "post_evidence",
                                UsageChannel::ComplianceSummaryRead => "get_compliance_summary",
                            },
                            "limit": limit,
                            "used": current,
                            "current": current,
                        })),
                    )
                    .into_response(),
                    api_usage::UsageError::Database(d) => api_error(
                        StatusCode::INTERNAL_SERVER_ERROR,
                        "USAGE_TRACKING_ERROR",
                        "We could not track API usage for this key.",
                        "Retry in a moment. If this persists, contact support (this is a server-side issue).",
                        Some(serde_json::Value::String(d)),
                    )
                    .into_response(),
                };
            }
        }
    }

    next.run(request).await
}

/// Ledger tenant resolved in API-key gate middleware (env or DB-issued keys).
#[derive(Clone, Debug)]
pub struct ResolvedLedgerTenant(pub String);

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use axum::routing::get;
    use axum::{middleware, Router};
    use serde_json::Value;
    use std::collections::HashMap;
    use std::sync::Arc;
    use tower::ServiceExt;

    fn usage_state_for_tests() -> ApiUsageState {
        let pool = sqlx::PgPool::connect_lazy("postgres://postgres:postgres@localhost/postgres")
            .expect("connect_lazy should not contact the database");
        ApiUsageState::from_env(&pool).expect("usage state should initialize in memory mode")
    }

    fn gate_state_for_tests(cfg: AuditApiKeyConfig, usage: ApiUsageState) -> AuditKeyGateState {
        let pool = sqlx::PgPool::connect_lazy("postgres://postgres:postgres@localhost/postgres")
            .expect("connect_lazy");
        AuditKeyGateState {
            cfg,
            usage,
            pool,
            deployment_env: GovaiEnvironment::Dev,
        }
    }

    #[tokio::test]
    async fn missing_api_key_returns_standard_error() {
        let usage = usage_state_for_tests();
        let cfg = AuditApiKeyConfig {
            keys: Some(Arc::new(HashMap::from([("good-key".to_string(), None)]))),
        };
        let gate = gate_state_for_tests(cfg, usage);

        let app = Router::new()
            .route("/bundle", get(|| async { "ok" }))
            .layer(middleware::from_fn_with_state(
                gate,
                gate_audit_routes_with_state,
            ));

        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/bundle")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
        let bytes = http_body_util::BodyExt::collect(resp.into_body())
            .await
            .unwrap()
            .to_bytes();
        let v: Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(
            v.pointer("/error/code").and_then(Value::as_str),
            Some("MISSING_API_KEY")
        );
    }

    #[tokio::test]
    async fn invalid_api_key_returns_standard_error() {
        let usage = usage_state_for_tests();
        let cfg = AuditApiKeyConfig {
            keys: Some(Arc::new(HashMap::from([("good-key".to_string(), None)]))),
        };
        let gate = gate_state_for_tests(cfg, usage);

        let app = Router::new()
            .route("/bundle", get(|| async { "ok" }))
            .layer(middleware::from_fn_with_state(
                gate,
                gate_audit_routes_with_state,
            ));

        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/bundle")
                    .header("Authorization", "Bearer bad-key")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
        let bytes = http_body_util::BodyExt::collect(resp.into_body())
            .await
            .unwrap()
            .to_bytes();
        let v: Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(
            v.pointer("/error/code").and_then(Value::as_str),
            Some("INVALID_API_KEY")
        );
    }

    #[test]
    fn parse_api_keys_allowlist_strips_per_key_limits() {
        let set = parse_api_keys_allowlist("k1, k2:25 ,k3:foo:42, ,k4");
        // Per-key cap suffix `:N` is stripped; `k3:foo` has no integer suffix so the colon stays.
        assert!(set.contains("k1"));
        assert!(set.contains("k2"));
        assert!(set.contains("k3:foo"));
        assert!(set.contains("k4"));
        assert_eq!(set.len(), 4);
    }

    #[test]
    fn parse_api_key_tenant_map_from_env_value_handles_empty_and_malformed() {
        assert!(parse_api_key_tenant_map_from_env_value("")
            .unwrap()
            .is_empty());
        assert!(parse_api_key_tenant_map_from_env_value("   ")
            .unwrap()
            .is_empty());
        assert!(parse_api_key_tenant_map_from_env_value("not-json").is_err());

        let m = parse_api_key_tenant_map_from_env_value(r#"{"k1":"t1","k2":"t2"," k3 ":"t3"}"#)
            .expect("valid json");
        assert_eq!(m.get("k1").map(String::as_str), Some("t1"));
        assert_eq!(m.get("k3").map(String::as_str), Some("t3"));
    }

    use std::sync::{Mutex, OnceLock};

    fn validator_env_lock() -> &'static Mutex<()> {
        static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
        LOCK.get_or_init(|| Mutex::new(()))
    }

    struct ScopedEnv {
        prev: Vec<(&'static str, Option<std::ffi::OsString>)>,
    }

    impl ScopedEnv {
        fn new(keys: &[&'static str]) -> Self {
            let prev = keys.iter().map(|k| (*k, std::env::var_os(k))).collect();
            Self { prev }
        }
    }

    impl Drop for ScopedEnv {
        fn drop(&mut self) {
            for (k, v) in self.prev.drain(..) {
                match v {
                    Some(val) => std::env::set_var(k, val),
                    None => std::env::remove_var(k),
                }
            }
        }
    }

    #[test]
    fn validate_api_key_allowlist_consistency_dev_warns_but_returns_ok() {
        let _g = validator_env_lock().lock().unwrap();
        let _scoped = ScopedEnv::new(&["GOVAI_API_KEYS", "GOVAI_API_KEYS_JSON"]);
        std::env::set_var("GOVAI_API_KEYS", "k1");
        std::env::set_var("GOVAI_API_KEYS_JSON", r#"{"k1":"t1","k2":"t2"}"#);
        let res = validate_api_key_allowlist_consistency(GovaiEnvironment::Dev);
        assert!(res.is_ok(), "dev should warn-only, got: {res:?}");
    }

    #[test]
    fn validate_api_key_allowlist_consistency_prod_fails_when_orphan_present() {
        let _g = validator_env_lock().lock().unwrap();
        let _scoped = ScopedEnv::new(&["GOVAI_API_KEYS", "GOVAI_API_KEYS_JSON"]);
        std::env::set_var("GOVAI_API_KEYS", "k1");
        std::env::set_var(
            "GOVAI_API_KEYS_JSON",
            r#"{"k1":"t1","k_orphan":"t_orphan"}"#,
        );
        let err = validate_api_key_allowlist_consistency(GovaiEnvironment::Prod)
            .expect_err("prod should fail when JSON has key not in allowlist");
        assert!(
            err.contains("not present in GOVAI_API_KEYS"),
            "unexpected error message: {err}"
        );
        let orphan_fp = key_fingerprint("k_orphan");
        assert!(
            err.contains(&orphan_fp),
            "expected sha256 fingerprint of orphan key in message: {err}"
        );
        assert!(
            !err.contains("k_orphan"),
            "raw API key must never appear in the error message: {err}"
        );
    }

    #[test]
    fn validate_api_key_allowlist_consistency_prod_passes_when_consistent() {
        let _g = validator_env_lock().lock().unwrap();
        let _scoped = ScopedEnv::new(&["GOVAI_API_KEYS", "GOVAI_API_KEYS_JSON"]);
        std::env::set_var("GOVAI_API_KEYS", "k1, k2:50 ");
        std::env::set_var("GOVAI_API_KEYS_JSON", r#"{"k1":"t1","k2":"t2"}"#);
        validate_api_key_allowlist_consistency(GovaiEnvironment::Prod)
            .expect("prod should pass when allowlist covers JSON keys (per-key caps stripped)");
    }
}
