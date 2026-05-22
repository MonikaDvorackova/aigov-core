use crate::api_usage::key_fingerprint;
use crate::api_usage::ApiUsageState;
use crate::audit_api_key;
use crate::auth::{AuthConfig, CurrentUser};
use crate::billing_trace;
use crate::bundle;
use crate::db::{self, DbPool};
use crate::evidence_usage;
use crate::govai_environment::GovaiEnvironment;
use crate::metering::{self, GovaiPlan, MeteringConfig, MeteringReject};
use crate::policy_store::PolicyStore;
use crate::pricing;
use crate::project;
use crate::projection;
use crate::rbac;
use crate::schema::EvidenceEvent;
use crate::stripe_billing;
use crate::stripe_webhook;
use crate::tenant_console_contract;
use crate::verify_chain;

use axum::body::Bytes;
use axum::extract::{Path, Query, Request, State};
use axum::http::{HeaderMap, StatusCode};
use axum::middleware::{self, Next};
use axum::response::IntoResponse;
use axum::routing::{get, post};
use axum::{Json, Router};
use chrono::{DateTime, Datelike, SecondsFormat, TimeZone, Utc};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::cmp::Ordering;
use uuid::Uuid;

use crate::api_error::{api_error, api_error_with};
use crate::ledger_storage;

fn clean_policy_prefix(s: &str) -> &str {
    s.trim()
        .strip_prefix("policy_violation:")
        .map(|x| x.trim())
        .unwrap_or_else(|| s.trim())
}

async fn post_ingest_product_milestones(
    pool: &DbPool,
    ledger_tid: &str,
    run_id: &str,
    next_count: u64,
    is_new_run: bool,
) {
    let _ = crate::product_ops::try_record_first_milestone(
        pool,
        ledger_tid,
        "first_evidence_ingest",
        Some(run_id),
        json!({ "event_count": next_count, "is_new_run": is_new_run }),
    )
    .await;
    let _ = crate::product_ops::recompute_tenant_health(pool, ledger_tid).await;
}

fn api_err(
    status: StatusCode,
    code: &str,
    message: &str,
    hint: &str,
    details: Option<serde_json::Value>,
    policy_version: Option<&str>,
    extra_top_level: Option<serde_json::Value>,
) -> (StatusCode, Json<serde_json::Value>) {
    let mut extra = serde_json::Map::new();
    if let Some(pv) = policy_version {
        extra.insert(
            "policy_version".to_string(),
            serde_json::Value::String(pv.to_string()),
        );
    }
    if let Some(ex) = extra_top_level {
        if let serde_json::Value::Object(obj) = ex {
            for (k, v) in obj {
                extra.insert(k, v);
            }
        }
    }
    let extra = if extra.is_empty() {
        None
    } else {
        Some(serde_json::Value::Object(extra))
    };
    api_error_with(status, code, message, hint, details, extra)
}

/// Ledger view used for deterministic policy evaluation at ingest time.
///
/// This is intentionally conservative:
/// - missing ledger file => empty iterator
/// - parse errors => treated as hard policy failures (fail-closed via caller)
struct LedgerFileView {
    log_path: String,
}

impl crate::policy_engine::LedgerView for LedgerFileView {
    fn iter_events_for_run<'a>(
        &'a self,
        run_id: &'a str,
    ) -> Box<dyn Iterator<Item = EvidenceEvent> + 'a> {
        // We must not panic here. Errors are surfaced as a single synthetic event
        // that will deterministically fail gates when required.
        let scan = crate::audit_store::scan_ledger_records(self.log_path.as_str());
        let events: Vec<EvidenceEvent> = match scan {
            Ok((records, _diag)) => {
                let mut out: Vec<EvidenceEvent> = Vec::new();
                for rec in records {
                    if let Ok(ev) = serde_json::from_str::<EvidenceEvent>(&rec.event_json) {
                        if ev.run_id == run_id {
                            out.push(ev);
                        }
                    } else {
                        // Fail-closed: inject a marker event that will never satisfy
                        // any real gate but allows evaluation to proceed deterministically.
                        out.push(EvidenceEvent {
                            event_id: "policy_parse_error".to_string(),
                            event_type: "policy_parse_error".to_string(),
                            ts_utc: "1970-01-01T00:00:00Z".to_string(),
                            actor: "system".to_string(),
                            system: "govai".to_string(),
                            run_id: run_id.to_string(),
                            environment: None,
                            payload: json!({ "error": "log_parse_error" }),
                        });
                        break;
                    }
                }
                out
            }
            Err(_) => Vec::new(),
        };

        Box::new(events.into_iter())
    }
}

fn normalize_error_code(raw: &str) -> String {
    raw.trim()
        .chars()
        .map(|c| match c {
            'a'..='z' => c.to_ascii_uppercase(),
            'A'..='Z' | '0'..='9' => c,
            _ => '_',
        })
        .collect::<String>()
        .trim_matches('_')
        .to_string()
}

fn tenant_scoped_not_found_hint() -> &'static str {
    "The resource was not found under the current tenant context. Check the run_id and API key. Note: X-GovAI-Project does not determine the ledger tenant."
}

/// Backward-compatible shim for older call sites. Prefer `api_err` for new code.
pub fn json_error(
    status: StatusCode,
    error: &str,
    message: &str,
    policy_version: Option<&str>,
    extra: Option<serde_json::Value>,
) -> (StatusCode, Json<serde_json::Value>) {
    let code = normalize_error_code(error);
    let (details, extra_top) = match extra {
        None => (None, None),
        Some(serde_json::Value::Object(mut obj)) => {
            let details = obj.remove("details");
            let extra = if obj.is_empty() {
                None
            } else {
                Some(serde_json::Value::Object(obj))
            };
            (details, extra)
        }
        Some(v) => (Some(v), None),
    };
    api_err(
        status,
        &code,
        message,
        "Retry. If this persists, contact support.",
        details,
        policy_version,
        extra_top,
    )
}

pub fn core_router(policy_version: &'static str, deployment_env: GovaiEnvironment) -> Router {
    Router::new()
        .route("/", get(root))
        .route("/health", get(health))
        .route("/metrics", get(crate::http_observability::metrics_handler))
        .route(
            "/pricing",
            get({
                let pv = policy_version;
                move || async move { pricing(pv).await }
            }),
        )
        .route(
            "/status",
            get({
                let pv = policy_version;
                let de = deployment_env;
                move || async move { status(pv, de).await }
            }),
        )
}

pub async fn root() -> (StatusCode, Json<serde_json::Value>) {
    (
        StatusCode::OK,
        Json(json!({
            "ok": true,
            "service": "govai",
            "version": env!("CARGO_PKG_VERSION"),
            "product_positioning": crate::tenant_console_contract::product_positioning_v1(),
        })),
    )
}

/// Liveness only (no DB or disk checks). For Postgres + migrations + ledger checks use **`GET /ready`** on the audit router.
pub async fn health() -> (StatusCode, Json<serde_json::Value>) {
    crate::runtime_metrics::set_health_ok(true);
    (StatusCode::OK, Json(json!({ "ok": true })))
}

pub async fn status(
    policy_version: &'static str,
    deployment_env: GovaiEnvironment,
) -> Json<serde_json::Value> {
    let base_url = std::env::var("GOVAI_BASE_URL")
        .or_else(|_| std::env::var("AIGOV_BASE_URL"))
        .ok()
        .map(|s| s.trim().trim_end_matches('/').to_string())
        .filter(|s| !s.is_empty());
    let gov_enf = GovernanceEnforcementMode::from_env();
    let allow_nonempty = !governance_enforcement_tenant_allowlist_from_env().is_empty();
    Json(json!({
        "ok": true,
        "policy_version": policy_version,
        "environment": deployment_env.as_str(),
        "base_url": base_url,
        "runtime_governance_enforcement": runtime_governance_enforcement_diag(gov_enf, allow_nonempty),
        "product_positioning": crate::tenant_console_contract::product_positioning_v1(),
    }))
}

pub async fn pricing(policy_version: &'static str) -> (StatusCode, Json<serde_json::Value>) {
    let _ = policy_version;
    let plans = pricing::get_plans()
        .into_iter()
        .map(|p| {
            json!({
                "name": p.name,
                "display_name": pricing::commercial_tier_display_name(p.name),
                "evidence_events_per_month": p.evidence_events_per_month,
                "runs_per_month": p.runs_per_month,
                "events_per_run": p.events_per_run
            })
        })
        .collect::<Vec<_>>();

    let pro_checkout_price_configured = stripe_billing::default_pro_checkout_price_id().is_ok();

    (
        StatusCode::OK,
        Json(json!({
            "units": {
                "primary": "evidence_event",
                "secondary": "run"
            },
            "definitions": {
                "evidence_event": "successful POST /evidence append",
                "run": "unique run_id with at least one event per month"
            },
            "plans": plans,
            "commercial": {
                "currency": "EUR",
                "pro_list_price_monthly": pricing::PRO_LIST_PRICE_EUR_MONTHLY,
                "marketing_tiers": ["Free", "Pro", "Enterprise", "Strategic Programs"],
                "self_serve_checkout_tier": "pro",
                "pro_checkout_price_configured": pro_checkout_price_configured,
                "plan_mapping": {
                    "api_plan_ids": ["free", "pro", "enterprise"],
                    "legacy_api_alias": { "team": "enterprise" },
                    "stripe_pro_price_env": ["GOVAI_STRIPE_PRICE_PRO", "GOVAI_STRIPE_PRICE_TEAM"],
                    "stripe_enterprise_price_env": "GOVAI_STRIPE_PRICE_ENTERPRISE"
                }
            }
        })),
    )
}

#[derive(Deserialize)]
struct BundleQuery {
    run_id: String,
}

#[derive(Deserialize)]
struct BundleHashQuery {
    run_id: String,
}

fn normalize_env_label(raw: &str) -> Option<&'static str> {
    match raw.trim().to_ascii_lowercase().as_str() {
        "dev" | "development" | "local" => Some("dev"),
        "staging" | "stage" => Some("staging"),
        "prod" | "production" => Some("prod"),
        _ => None,
    }
}

/// Reject cross-environment mixing for a run; stamp [`EvidenceEvent::environment`] to the server tier.
fn prepare_event_for_ingest(
    event: &mut EvidenceEvent,
    deployment: GovaiEnvironment,
    log_path: &str,
) -> Result<Vec<EvidenceEvent>, String> {
    let canon = deployment.as_str();
    if let Some(ref claimed) = event.environment {
        let norm = normalize_env_label(claimed)
            .ok_or_else(|| format!("policy_violation: invalid event.environment={claimed:?}"))?;
        if norm != canon {
            return Err(format!(
                "policy_violation: event.environment={claimed:?} does not match server deployment {canon}"
            ));
        }
    }

    let existing = bundle::collect_events_for_run(log_path, &event.run_id)?;
    for e in &existing {
        if let Some(ref pe) = e.environment {
            let norm = normalize_env_label(pe).ok_or_else(|| {
                format!(
                    "policy_violation: log contains invalid environment={pe:?} on event_id={}",
                    e.event_id
                )
            })?;
            if norm != canon {
                return Err(format!(
                    "policy_violation: run_id {} already tagged environment={pe:?}; refusing {canon}",
                    event.run_id
                ));
            }
        }
    }

    event.environment = Some(canon.to_string());
    Ok(existing)
}

#[derive(Clone)]
pub struct AuditState {
    pub ledger_base: &'static str,
    pub policy_version: &'static str,
    pub deployment_env: GovaiEnvironment,
    pub policy_store: PolicyStore,
    pub pool: DbPool,
    pub metering: MeteringConfig,
}

async fn stripe_webhook_route(
    State(audit): State<AuditState>,
    headers: HeaderMap,
    body: Bytes,
) -> (StatusCode, Json<serde_json::Value>) {
    let sig = headers
        .get(axum::http::HeaderName::from_static("stripe-signature"))
        .and_then(|v| v.to_str().ok());
    let (status, j) = stripe_webhook::handle_stripe_webhook(&audit.pool, body.as_ref(), sig).await;
    (status, Json(j))
}

async fn billing_enforcement_middleware(
    State(audit): State<AuditState>,
    request: Request,
    next: Next,
) -> axum::response::Response {
    let path = request.uri().path().to_string();
    if stripe_billing::billing_enforcement_exempt_path(path.as_str()) {
        return next.run(request).await;
    }
    if !stripe_billing::billing_enforcement_enabled() {
        return next.run(request).await;
    }
    let headers = request.headers().clone();
    let tenant_res =
        stripe_billing::ledger_tenant_for_billing_headers(&headers, audit.deployment_env);
    let tenant_id = match tenant_res {
        Ok(t) => t,
        Err(_) => {
            return (
                StatusCode::UNAUTHORIZED,
                Json(json!({
                    "ok": false,
                    "error": {
                        "code": "MISSING_API_KEY",
                        "message": "Missing API key.",
                        "hint": "Provide `Authorization: Bearer <api_key>`."
                    }
                })),
            )
                .into_response();
        }
    };
    match stripe_billing::tenant_subscription_gate(&audit.pool, &tenant_id).await {
        Ok(true) => next.run(request).await,
        Ok(false) => (
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "error": {
                    "code": "BILLING_INACTIVE",
                    "message": "Billing subscription is not active.",
                    "hint": "Update payment details in the billing portal or complete checkout."
                }
            })),
        )
            .into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({
                "ok": false,
                "error": {
                    "code": "BILLING_GATE_ERROR",
                    "message": "Could not verify billing state.",
                    "hint": "Retry in a moment. If this persists, contact support.",
                    "details": { "raw": e.to_string() }
                }
            })),
        )
            .into_response(),
    }
}

/// Returns `(ledger_file_path, ledger_tenant_id)`; tenant id is API-key-derived only.
fn tenant_log_path(audit: &AuditState, headers: &HeaderMap) -> Result<(String, String), String> {
    let tenant_id = project::require_tenant_id_for_ledger(headers, audit.deployment_env)?;
    Ok((
        project::resolve_ledger_path(audit.ledger_base, &tenant_id),
        tenant_id,
    ))
}

/// Ingest phases after [`crate::audit_api_key::gate_audit_routes`]:
/// 1. Prepare + policy validation  
/// 2. Duplicate rejection  
/// 3. Legacy billing tenant ([`project::billing_tenant_id`]) when `GOVAI_METERING` is off — same scope as `GET /usage`  
/// 4. Metering precheck (`GOVAI_METERING=on`) **or** legacy evidence quota  
/// 5. [`crate::audit_store::append_record`]  
/// 6. Metering persist **or** [`evidence_usage::increment_evidence_usage`]
async fn ingest(
    State(audit): State<AuditState>,
    headers: HeaderMap,
    Json(mut event): Json<EvidenceEvent>,
) -> (StatusCode, Json<serde_json::Value>) {
    let (log_path, ledger_tid) = match tenant_log_path(&audit, &headers) {
        Ok(p) => p,
        Err(e) => {
            return api_err(
                StatusCode::BAD_REQUEST,
                "MISSING_TENANT_CONTEXT",
                "Missing tenant context.",
                "Provide `Authorization: Bearer <api_key>`.",
                Some(serde_json::Value::String(e)),
                Some(audit.policy_version),
                None,
            );
        }
    };

    let existing = match prepare_event_for_ingest(&mut event, audit.deployment_env, &log_path) {
        Ok(x) => x,
        Err(e) => {
            return api_err(
                StatusCode::BAD_REQUEST,
                "POLICY_VIOLATION",
                clean_policy_prefix(&e),
                "Fix the request payload to satisfy the environment/policy constraints and retry.",
                Some(json!({ "raw": e, "policy_code": "environment_policy" })),
                Some(audit.policy_version),
                None,
            );
        }
    };

    // Deterministic, declarative policy enforcement (bundle policy if configured; else legacy adapter).
    let ledger = LedgerFileView {
        log_path: log_path.clone(),
    };
    if let Err(e) = audit
        .policy_store
        .enforce_ingest_for_request(&ledger_tid, &event, &ledger)
    {
        return api_err(
            StatusCode::BAD_REQUEST,
            "POLICY_VIOLATION",
            clean_policy_prefix(&e.message),
            "Fix the request payload to satisfy the policy and retry.",
            Some(json!({ "raw": e.message, "policy_code": e.code })),
            Some(audit.policy_version),
            None,
        );
    }

    if let Err(msg) =
        crate::product_ops::ingest_autonomy_gate(&audit.pool, &ledger_tid, &event).await
    {
        let (code, hint) = if msg.contains("AUTONOMY_POLICY_REQUIRED") {
            (
                "AUTONOMY_POLICY_REQUIRED",
                "Provision a row in govai_tenant_autonomy_policy for this ledger tenant, or remove governance.autonomous_action from the payload.",
            )
        } else {
            (
                "AUTONOMY_BLOCKED",
                "Adjust governance.autonomous_action (capability, stop/kill posture) or relax the persisted autonomy policy for this tenant.",
            )
        };
        return api_err(
            StatusCode::FORBIDDEN,
            code,
            "Autonomous governance rejected this evidence ingest.",
            hint,
            Some(json!({ "raw": msg })),
            Some(audit.policy_version),
            None,
        );
    }

    // Used for usage counters after a successful append (avoid double counting on rejected ingests).
    let is_discovery_scan = event.event_type == "ai_discovery_reported";

    // Legacy `govai_usage_counters` tenant (only when `GOVAI_METERING` is off); same scope as `GET /usage`.
    let tenant_id_legacy = if !audit.metering.enabled {
        Some(project::billing_tenant_id(&headers))
    } else {
        None
    };

    let run_id = event.run_id.clone();

    // Used for metering/quota prechecks (append remains authoritative and atomic).
    let pre_count = existing.len() as u64;
    let next_count = pre_count + 1;
    let is_new_run = pre_count == 0;

    let metering_team = if audit.metering.enabled {
        let key_hash = match audit_api_key::raw_bearer_token(&headers) {
            None => {
                return api_err(
                    StatusCode::UNAUTHORIZED,
                    "MISSING_API_KEY",
                    "Missing API key.",
                    "Provide `Authorization: Bearer <api_key>`.",
                    None,
                    None,
                    None,
                );
            }
            Some(t) => key_fingerprint(t),
        };
        let team_id = match metering::team_id_for_key_hash(&audit.pool, &key_hash).await {
            Ok(t) => t,
            Err(e) => {
                return api_err(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "METERING_ERROR",
                    "We could not load metering information for this API key.",
                    "Retry in a moment. If this persists, contact support (this is a server-side issue).",
                    Some(json!({ "raw": e.to_string() })),
                    Some(audit.policy_version),
                    None,
                );
            }
        };
        let team_id = match team_id {
            None => {
                return api_err(
                    StatusCode::FORBIDDEN,
                    "TEAM_NOT_CONFIGURED",
                    "This API key is valid, but it is not linked to a billing team.",
                    "Ask an admin to configure billing for this API key (or use a key that is linked to a team).",
                    None,
                    Some(audit.policy_version),
                    None,
                );
            }
            Some(t) => t,
        };
        let plan = audit.metering.default_plan;
        let limits = metering::PlanLimits::for_plan(plan);
        let ym = metering::year_month_utc_now();
        let (new_run_ids, evidence_events) = match metering::load_monthly(&audit.pool, team_id, ym)
            .await
        {
            Ok(x) => x,
            Err(e) => {
                return api_err(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "METERING_ERROR",
                    "We could not load metering counters.",
                    "Retry in a moment. If this persists, contact support (this is a server-side issue).",
                    Some(json!({ "raw": e.to_string() })),
                    Some(audit.policy_version),
                    None,
                );
            }
        };
        let unlimited_monthly = metering::is_unlimited_metering_team(&team_id);

        if let Err(r) = metering::precheck_ingest(
            plan,
            limits,
            new_run_ids,
            evidence_events,
            is_new_run,
            &run_id,
            next_count,
            unlimited_monthly,
        ) {
            let team_s = team_id.to_string();
            let plan_s = plan_id_str(plan);
            return match r {
                MeteringReject::MonthlyRunLimit { used, limit } => api_err(
                    StatusCode::TOO_MANY_REQUESTS,
                    "MONTHLY_RUN_LIMIT_EXCEEDED",
                    "Monthly run limit exceeded for this team.",
                    "Start a new month, or upgrade your plan.",
                    Some(json!({ "used": used, "limit": limit })),
                    Some(audit.policy_version),
                    Some(json!({
                        "metering": "on",
                        "count_kind": "new_runs_month",
                        "team_id": team_s,
                        "plan": plan_s,
                        "used": used,
                        "limit": limit,
                        "year_month": ym,
                    })),
                ),
                MeteringReject::MonthlyEventLimit { used, limit } => api_err(
                    StatusCode::TOO_MANY_REQUESTS,
                    "MONTHLY_EVENT_LIMIT_EXCEEDED",
                    "Monthly evidence event limit exceeded for this team.",
                    "Start a new month, or upgrade your plan.",
                    Some(json!({ "used": used, "limit": limit })),
                    Some(audit.policy_version),
                    Some(json!({
                        "metering": "on",
                        "count_kind": "evidence_events_month",
                        "team_id": team_s,
                        "plan": plan_s,
                        "used": used,
                        "limit": limit,
                        "year_month": ym,
                    })),
                ),
                MeteringReject::PerRunEventLimit {
                    run_id,
                    would_be,
                    limit,
                } => api_err(
                    StatusCode::TOO_MANY_REQUESTS,
                    "PER_RUN_EVENT_LIMIT_EXCEEDED",
                    "This run has reached its per-run evidence event limit.",
                    "Use a new `run_id`, or upgrade your plan.",
                    Some(
                        json!({ "used": pre_count, "would_be": would_be, "limit": limit, "run_id": run_id }),
                    ),
                    Some(audit.policy_version),
                    Some(json!({
                        "metering": "on",
                        "count_kind": "evidence_events_per_run",
                        "team_id": team_s,
                        "plan": plan_s,
                        "run_id": run_id,
                        "used": pre_count,
                        "event_count": would_be,
                        "limit": limit,
                        "year_month": ym,
                    })),
                ),
            };
        }
        Some((team_id, plan, ym, limits, new_run_ids, evidence_events))
    } else {
        None
    };

    if let Some(ref tid) = tenant_id_legacy {
        match evidence_usage::check_evidence_quota(&audit.pool, tid).await {
            Ok(()) => {}
            Err(evidence_usage::CheckEvidenceQuotaError::Exceeded(q)) => {
                return (
                    StatusCode::TOO_MANY_REQUESTS,
                    api_err(
                        StatusCode::TOO_MANY_REQUESTS,
                        "MONTHLY_EVENT_LIMIT_EXCEEDED",
                        "Monthly evidence event limit exceeded for this tenant.",
                        "Wait until the next billing period, or enable metering / upgrade your plan.",
                        Some(json!({ "used": q.used, "limit": q.limit, "period_start": q.period_start.format("%Y-%m-%d").to_string() })),
                        Some(audit.policy_version),
                        Some(json!({
                            "metering": "off",
                            "count_kind": "evidence_events",
                            "tenant_id": tid,
                            "used": q.used,
                            "limit": q.limit,
                            "period_start": q.period_start.format("%Y-%m-%d").to_string(),
                        })),
                    )
                    .1,
                );
            }
            Err(evidence_usage::CheckEvidenceQuotaError::Database(e)) => {
                return api_err(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "DB_ERROR",
                    "We could not read usage counters.",
                    "Retry in a moment. If this persists, contact support (this is a server-side issue).",
                    Some(json!({ "raw": e })),
                    Some(audit.policy_version),
                    None,
                );
            }
        }
    }

    match crate::audit_store::append_record_atomic_with_run_count(&log_path, event) {
        Ok((rec, pre_count_usize)) => {
            let pre_count = pre_count_usize as u64;
            let next_count = pre_count + 1;
            let is_new_run = pre_count == 0;
            if let Some((team_id, plan, ym, limits, new_run_ids, evidence_events)) = metering_team {
                if let Err(e) = metering::record_successful_ingest(
                    &audit.pool,
                    team_id,
                    ym,
                    &run_id,
                    next_count as i64,
                    is_new_run,
                )
                .await
                {
                    return api_err(
                        StatusCode::INTERNAL_SERVER_ERROR,
                        "METERING_PERSIST_ERROR",
                        "The event was appended, but metering counters could not be updated.",
                        "Retry in a moment. If this persists, contact support (this is a server-side issue).",
                        Some(json!({ "raw": e })),
                        Some(audit.policy_version),
                        None,
                    );
                }

                // Operational usage: discovery scans are counted when discovery evidence is accepted.
                if is_discovery_scan {
                    let _ = metering::increment_team_op_counter(
                        &audit.pool,
                        team_id,
                        ym,
                        metering::TeamOpCounter::DiscoveryScan,
                    )
                    .await;
                }

                billing_trace::record_evidence_ingest_unit(&audit.pool, &ledger_tid, &run_id).await;
                let _ = stripe_billing::record_usage_attribution(
                    &audit.pool,
                    &ledger_tid,
                    stripe_billing::BILLING_UNIT_EVIDENCE_EVENT,
                    &run_id,
                    None,
                )
                .await;
                if is_discovery_scan {
                    let _ = stripe_billing::record_usage_attribution(
                        &audit.pool,
                        &ledger_tid,
                        stripe_billing::BILLING_UNIT_DISCOVERY_SCAN,
                        &run_id,
                        None,
                    )
                    .await;
                }

                post_ingest_product_milestones(
                    &audit.pool,
                    &ledger_tid,
                    &run_id,
                    next_count,
                    is_new_run,
                )
                .await;

                let nr1 = new_run_ids + if is_new_run { 1 } else { 0 };
                let ev1 = evidence_events + 1;
                let warnings = metering::basic_warnings(
                    plan,
                    limits,
                    nr1,
                    ev1,
                    is_new_run,
                    metering::is_unlimited_metering_team(&team_id),
                );
                let complexity = metering::run_complexity_label(next_count);
                (
                    StatusCode::OK,
                    Json(json!({
                        "ok": true,
                        "record_hash": rec.record_hash,
                        "policy_version": audit.policy_version,
                        "environment": audit.deployment_env.as_str(),
                        "team_id": team_id.to_string(),
                        "plan": plan_id_str(plan),
                        "year_month": ym,
                        "run": {
                            "run_id": run_id,
                            "event_count": next_count,
                            "run_complexity": complexity
                        },
                        "warnings": warnings
                    })),
                )
            } else {
                let tid = tenant_id_legacy
                    .as_ref()
                    .expect("legacy billing tenant when metering is off");
                if let Err(e) = evidence_usage::increment_evidence_usage(&audit.pool, tid).await {
                    return api_err(
                        StatusCode::INTERNAL_SERVER_ERROR,
                        "USAGE_PERSIST_ERROR",
                        "The event was appended, but usage counters could not be updated.",
                        "Retry in a moment. If this persists, contact support (this is a server-side issue).",
                        Some(json!({ "raw": e })),
                        Some(audit.policy_version),
                        None,
                    );
                }

                if is_discovery_scan {
                    if let Err(e) =
                        evidence_usage::increment_discovery_scan_usage(&audit.pool, tid).await
                    {
                        return api_err(
                            StatusCode::INTERNAL_SERVER_ERROR,
                            "USAGE_PERSIST_ERROR",
                            "The event was appended, but usage counters could not be updated.",
                            "Retry in a moment. If this persists, contact support (this is a server-side issue).",
                            Some(json!({ "raw": e })),
                            Some(audit.policy_version),
                            None,
                        );
                    }
                }

                billing_trace::record_evidence_ingest_unit(&audit.pool, &ledger_tid, &run_id).await;
                let _ = stripe_billing::record_usage_attribution(
                    &audit.pool,
                    &ledger_tid,
                    stripe_billing::BILLING_UNIT_EVIDENCE_EVENT,
                    &run_id,
                    None,
                )
                .await;
                if is_discovery_scan {
                    let _ = stripe_billing::record_usage_attribution(
                        &audit.pool,
                        &ledger_tid,
                        stripe_billing::BILLING_UNIT_DISCOVERY_SCAN,
                        &run_id,
                        None,
                    )
                    .await;
                }

                post_ingest_product_milestones(
                    &audit.pool,
                    &ledger_tid,
                    &run_id,
                    next_count,
                    is_new_run,
                )
                .await;

                (
                    StatusCode::OK,
                    Json(json!({
                        "ok": true,
                        "record_hash": rec.record_hash,
                        "policy_version": audit.policy_version,
                        "environment": audit.deployment_env.as_str(),
                    })),
                )
            }
        }
        Err(e) => {
            if e.contains("duplicate event_id for run_id") {
                api_err(
                    StatusCode::CONFLICT,
                    "DUPLICATE_EVENT_ID",
                    "This event_id already exists for this run_id.",
                    "Use a new `event_id`, or treat this request as an idempotent retry and stop sending duplicates.",
                    Some(json!({ "raw": e })),
                    Some(audit.policy_version),
                    None,
                )
            } else {
                let cwd = std::env::current_dir()
                    .map(|p| p.display().to_string())
                    .unwrap_or_else(|_| "(unavailable)".to_string());
                let ledger_dir = crate::ledger_storage::configured_ledger_dir()
                    .map(|p| p.display().to_string())
                    .unwrap_or_else(|| "(unset)".to_string());
                eprintln!(
                    "ingest: append_error tenant_id={} log_path={} cwd={} ledger_dir={} err={}",
                    ledger_tid, log_path, cwd, ledger_dir, e
                );
                api_err(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "APPEND_ERROR",
                    "We could not append this evidence event.",
                    "Retry in a moment. If this persists, contact support (this is a server-side issue).",
                    Some(json!({ "raw": e })),
                    Some(audit.policy_version),
                    None,
                )
            }
        }
    }
}

fn plan_id_str(p: GovaiPlan) -> &'static str {
    match p {
        GovaiPlan::Free => "free",
        GovaiPlan::Team => "team",
        GovaiPlan::Growth => "growth",
        GovaiPlan::Enterprise => "enterprise",
    }
}

async fn usage_route(
    State(audit): State<AuditState>,
    headers: HeaderMap,
) -> (StatusCode, Json<serde_json::Value>) {
    if audit.metering.enabled {
        let key_hash = match audit_api_key::raw_bearer_token(&headers) {
            None => {
                return api_err(
                    StatusCode::UNAUTHORIZED,
                    "MISSING_API_KEY",
                    "Missing API key.",
                    "Provide `Authorization: Bearer <api_key>`.",
                    None,
                    None,
                    None,
                );
            }
            Some(t) => key_fingerprint(t),
        };
        let team_id = match metering::team_id_for_key_hash(&audit.pool, &key_hash).await {
            Ok(t) => t,
            Err(e) => {
                return api_err(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "METERING_ERROR",
                    "We could not load metering information for this API key.",
                    "Retry in a moment. If this persists, contact support (this is a server-side issue).",
                    Some(json!({ "raw": e.to_string() })),
                    Some(audit.policy_version),
                    None,
                );
            }
        };
        let Some(team_id) = team_id else {
            return api_err(
                StatusCode::FORBIDDEN,
                "TEAM_NOT_CONFIGURED",
                "This API key is valid, but it is not linked to a billing team.",
                "Ask an admin to configure billing for this API key (or use a key that is linked to a team).",
                None,
                Some(audit.policy_version),
                None,
            );
        };
        let ledger_tenant = project::billing_tenant_id(&headers);
        let plan_name =
            match stripe_billing::commercial_plan_for_tenant(&audit.pool, &ledger_tenant).await {
                Ok(p) => p,
                Err(_) => {
                    pricing::resolve_plan(audit_api_key::raw_bearer_token(&headers).unwrap_or(""))
                        .to_string()
                }
            };
        let plan_limits = pricing::plan_limits_by_name(&plan_name).unwrap_or(pricing::PlanLimits {
            name: "free",
            evidence_events_per_month: 2_500,
            runs_per_month: 25,
            events_per_run: 1_000,
        });
        let ym = metering::year_month_utc_now();
        let (new_run_ids, evidence_events) = match metering::load_monthly(&audit.pool, team_id, ym)
            .await
        {
            Ok(x) => x,
            Err(e) => {
                return api_err(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "METERING_ERROR",
                    "We could not load metering counters.",
                    "Retry in a moment. If this persists, contact support (this is a server-side issue).",
                    Some(json!({ "raw": e.to_string() })),
                    Some(audit.policy_version),
                    None,
                );
            }
        };
        let (compliance_checks, exports, discovery_scans) = match metering::load_monthly_ops(
            &audit.pool,
            team_id,
            ym,
        )
        .await
        {
            Ok(x) => x,
            Err(e) => {
                return api_err(
                        StatusCode::INTERNAL_SERVER_ERROR,
                        "METERING_ERROR",
                        "We could not load usage counters.",
                        "Retry in a moment. If this persists, contact support (this is a server-side issue).",
                        Some(json!({ "raw": e.to_string() })),
                        Some(audit.policy_version),
                        None,
                    );
            }
        };
        let used_runs_u64 = new_run_ids.max(0) as u64;
        let used_events_u64 = evidence_events.max(0) as u64;
        let rem_runs = plan_limits.runs_per_month.saturating_sub(used_runs_u64);
        let rem_events = plan_limits
            .evidence_events_per_month
            .saturating_sub(used_events_u64);
        let metering_limits = metering::PlanLimits::for_plan(audit.metering.default_plan);
        return (
            StatusCode::OK,
            Json(json!({
                "metering": "on",
                "team_id": team_id.to_string(),
                "year_month": ym,
                "plan": plan_name,
                "new_run_ids": new_run_ids,
                "evidence_events": evidence_events,
                "compliance_checks": compliance_checks,
                "exports": exports,
                "discovery_scans": discovery_scans,
                // Additive normalized usage surface (do not remove existing fields).
                "usage": {
                    "evidence_events": used_events_u64,
                    "runs": used_runs_u64,
                    "compliance_checks": compliance_checks.max(0) as u64,
                    "exports": exports.max(0) as u64,
                    "discovery_scans": discovery_scans.max(0) as u64
                },
                "limits": {
                    "evidence_events": plan_limits.evidence_events_per_month,
                    "runs": plan_limits.runs_per_month,
                    "events_per_run": plan_limits.events_per_run
                },
                "remaining": {
                    "evidence_events": rem_events,
                    "runs": rem_runs
                },
                "legacy_metering_limits": {
                    "max_runs_per_month": metering_limits.max_runs_per_month,
                    "max_events_per_month": metering_limits.max_events_per_month,
                    "max_events_per_run": metering_limits.max_events_per_run
                }
            })),
        );
    }

    let tenant_id = project::billing_tenant_id(&headers);
    match evidence_usage::get_usage_counters(&audit.pool, &tenant_id).await {
        Ok((evidence_count, compliance_checks, exports, discovery_scans, period)) => {
            let used_events_u64 = evidence_count.max(0) as u64;
            let plan_name = stripe_billing::commercial_plan_for_tenant(&audit.pool, &tenant_id)
                .await
                .unwrap_or_else(|_| "free".to_string());
            let plan_limits =
                pricing::plan_limits_by_name(&plan_name).unwrap_or(pricing::PlanLimits {
                    name: "free",
                    evidence_events_per_month: 2_500,
                    runs_per_month: 25,
                    events_per_run: 1_000,
                });
            let rem_events = plan_limits
                .evidence_events_per_month
                .saturating_sub(used_events_u64);
            let rem_runs = plan_limits.runs_per_month;
            (
                StatusCode::OK,
                Json(json!({
                    "metering": "off",
                    "tenant_id": tenant_id,
                    "period_start": period.format("%Y-%m-%d").to_string(),
                    "evidence_events_count": evidence_count,
                    "compliance_checks_count": compliance_checks,
                    "exports_count": exports,
                    "discovery_scans_count": discovery_scans,
                    "limit": evidence_usage::FREE_TIER_EVIDENCE_LIMIT,
                    // Additive normalized usage surface.
                    "plan": plan_name,
                    "usage": {
                        "evidence_events": used_events_u64,
                        "runs": 0,
                        "compliance_checks": compliance_checks.max(0) as u64,
                        "exports": exports.max(0) as u64,
                        "discovery_scans": discovery_scans.max(0) as u64
                    },
                    "limits": {
                        "evidence_events": plan_limits.evidence_events_per_month,
                        "runs": plan_limits.runs_per_month,
                        "events_per_run": plan_limits.events_per_run
                    },
                    "remaining": {
                        "evidence_events": rem_events,
                        "runs": rem_runs
                    }
                })),
            )
        }
        Err(e) => api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "DB_ERROR",
            "We could not load usage for this tenant.",
            "Retry in a moment. If this persists, contact support (this is a server-side issue).",
            Some(json!({ "raw": e.to_string() })),
            Some(audit.policy_version),
            None,
        ),
    }
}

async fn verify(
    State(audit): State<AuditState>,
    headers: HeaderMap,
) -> (StatusCode, Json<serde_json::Value>) {
    let (log_path, _) = match tenant_log_path(&audit, &headers) {
        Ok(p) => p,
        Err(e) => {
            return api_err(
                StatusCode::BAD_REQUEST,
                "MISSING_TENANT_CONTEXT",
                "Missing tenant context.",
                "Provide `Authorization: Bearer <api_key>`.",
                Some(serde_json::Value::String(e)),
                Some(audit.policy_version),
                None,
            );
        }
    };
    if let Err(e) = crate::audit_store::verify_chain(&log_path) {
        return api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "CHAIN_INVALID",
            "The append-only chain failed verification. The ledger may have been corrupted.",
            "Retry later. If this persists, contact support (this is a server-side integrity issue).",
            Some(json!({ "raw": e })),
            Some(audit.policy_version),
            None,
        );
    }
    if let Err(e) = crate::audit_store::verify_checkpoints(&log_path) {
        return api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "CHECKPOINT_INVALID",
            "Ledger checkpoint verification failed. The ledger or checkpoint log may have been tampered with.",
            "Retry later. If this persists, contact support (this is a server-side integrity issue).",
            Some(json!({ "raw": e })),
            Some(audit.policy_version),
            None,
        );
    }
    (
        StatusCode::OK,
        Json(json!({ "ok": true, "policy_version": audit.policy_version })),
    )
}

async fn verify_immutable(
    State(audit): State<AuditState>,
    headers: HeaderMap,
) -> (StatusCode, Json<serde_json::Value>) {
    let (log_path, tenant_id) = match tenant_log_path(&audit, &headers) {
        Ok(p) => p,
        Err(e) => {
            return api_err(
                StatusCode::BAD_REQUEST,
                "MISSING_TENANT_CONTEXT",
                "Missing tenant context.",
                "Provide `Authorization: Bearer <api_key>`.",
                Some(serde_json::Value::String(e)),
                Some(audit.policy_version),
                None,
            );
        }
    };

    if let Err(e) = crate::audit_store::verify_chain(&log_path) {
        return api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "CHAIN_INVALID",
            "The append-only chain failed verification. The ledger may have been corrupted.",
            "Retry later. If this persists, contact support (this is a server-side integrity issue).",
            Some(json!({ "raw": e })),
            Some(audit.policy_version),
            None,
        );
    }
    if let Err(e) = crate::audit_store::verify_checkpoints(&log_path) {
        return api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "CHECKPOINT_INVALID",
            "Ledger checkpoint verification failed. The ledger or checkpoint log may have been tampered with.",
            "Retry later. If this persists, contact support (this is a server-side integrity issue).",
            Some(json!({ "raw": e })),
            Some(audit.policy_version),
            None,
        );
    }

    let cfg = match crate::immutable_store::ImmutableStoreConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return api_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "IMMUTABLE_CONFIG_INVALID",
                "Immutable audit backend configuration is invalid.",
                "Fix GOVAI_IMMUTABLE_BACKEND and related env vars.",
                Some(json!({ "raw": e })),
                Some(audit.policy_version),
                None,
            );
        }
    };
    if !cfg.validate_startup(audit.deployment_env).is_ok()
        || matches!(
            cfg.kind,
            crate::immutable_store::ImmutableBackendKind::Disabled
        )
    {
        return api_err(
            StatusCode::BAD_REQUEST,
            "IMMUTABLE_BACKEND_DISABLED",
            "Immutable audit backend is not enabled for this deployment.",
            "Enable GOVAI_IMMUTABLE_BACKEND=aws_s3_object_lock and configure the bucket.",
            None,
            Some(audit.policy_version),
            None,
        );
    }

    let store = match crate::immutable_store::ImmutableStore::init(cfg).await {
        Ok(s) => s,
        Err(e) => {
            return api_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "IMMUTABLE_BACKEND_INIT_FAILED",
                "Could not initialize immutable audit backend.",
                "Retry later. If this persists, contact support.",
                Some(json!({ "raw": e })),
                Some(audit.policy_version),
                None,
            );
        }
    };

    let Some(cp) = (match crate::audit_store::latest_checkpoint(&log_path) {
        Ok(x) => x,
        Err(e) => {
            return api_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "CHECKPOINT_READ_FAILED",
                "Could not read ledger checkpoints.",
                "Retry later. If this persists, contact support.",
                Some(json!({ "raw": e })),
                Some(audit.policy_version),
                None,
            );
        }
    }) else {
        return api_err(
            StatusCode::NOT_FOUND,
            "NO_CHECKPOINT",
            "No checkpoint exists for this tenant ledger yet.",
            "Generate an export to force a checkpoint, or submit evidence to create one.",
            None,
            Some(audit.policy_version),
            None,
        );
    };

    // Anchor id is the checkpoint digest (events_content_sha256) for deterministic lookup.
    let anchor_id = cp.events_content_sha256.clone();
    let got = match store.get_anchor_bytes(&tenant_id, &anchor_id).await {
        Ok(x) => x,
        Err(e) => {
            return api_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "IMMUTABLE_READ_FAILED",
                "Could not read immutable anchor object.",
                "Retry later. If this persists, contact support.",
                Some(json!({ "raw": e })),
                Some(audit.policy_version),
                None,
            );
        }
    };
    if got.is_none() {
        return api_err(
            StatusCode::NOT_FOUND,
            "IMMUTABLE_ANCHOR_MISSING",
            "Immutable anchor object is missing for the current ledger checkpoint.",
            "Run anchor-now or investigate immutable backend configuration and retention.",
            Some(json!({ "anchor_id": anchor_id })),
            Some(audit.policy_version),
            None,
        );
    }

    (
        StatusCode::OK,
        Json(json!({
          "ok": true,
          "policy_version": audit.policy_version,
          "tenant_id": tenant_id,
          "anchor_id": anchor_id
        })),
    )
}

async fn bundle_route(
    State(audit): State<AuditState>,
    headers: HeaderMap,
    Query(q): Query<BundleQuery>,
) -> (StatusCode, Json<serde_json::Value>) {
    let (log_path, _) = match tenant_log_path(&audit, &headers) {
        Ok(p) => p,
        Err(e) => {
            return api_err(
                StatusCode::BAD_REQUEST,
                "MISSING_TENANT_CONTEXT",
                "Missing tenant context.",
                "Provide `Authorization: Bearer <api_key>`.",
                Some(serde_json::Value::String(e)),
                Some(audit.policy_version),
                None,
            )
        }
    };
    match bundle::collect_events_for_run(&log_path, &q.run_id) {
        Ok(events) => {
            if events.is_empty() {
                return api_err(
                    StatusCode::NOT_FOUND,
                    "RUN_NOT_FOUND",
                    "No events were found for this run_id in the current tenant ledger.",
                    tenant_scoped_not_found_hint(),
                    None,
                    Some(audit.policy_version),
                    Some(json!({ "run_id": q.run_id })),
                );
            }
            let events = bundle::canonicalize_evidence_events(events);
            let lp = format!("rust/{}", log_path);
            let doc = bundle::bundle_document_value(&q.run_id, audit.policy_version, &lp, &events);
            (StatusCode::OK, Json(doc))
        }
        Err(e) => api_err(
            StatusCode::NOT_FOUND,
            "RUN_NOT_FOUND",
            "No events were found for this run_id in the current tenant ledger.",
            tenant_scoped_not_found_hint(),
            Some(json!({ "raw": e })),
            Some(audit.policy_version),
            Some(json!({ "run_id": q.run_id })),
        ),
    }
}

fn payload_get_str(p: &serde_json::Value, key: &str) -> Option<String> {
    p.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
}

fn payload_get_num(p: &serde_json::Value, key: &str) -> Option<f64> {
    p.get(key).and_then(|v| v.as_f64())
}

fn sha256_hex_str(s: &str) -> String {
    let mut h = Sha256::new();
    h.update(s.as_bytes());
    hex::encode(h.finalize())
}

#[derive(Debug, Clone)]
struct DiscoveryFindingOut {
    file_path: String,
    detector: String,
    confidence: f64,
    matched_pattern: Option<String>,
    hash: String,
}

fn extract_discovery_findings(events: &[EvidenceEvent]) -> Vec<DiscoveryFindingOut> {
    // Derive only from already-submitted evidence. Never run a scan during export.
    let Some(ev) = events
        .iter()
        .rev()
        .find(|e| e.event_type == "ai_discovery_reported")
    else {
        return Vec::new();
    };

    let p = &ev.payload;
    let Some(arr) = p.get("findings").and_then(|v| v.as_array()) else {
        return Vec::new();
    };

    let mut out: Vec<DiscoveryFindingOut> = Vec::new();
    for v in arr {
        let Some(obj) = v.as_object() else { continue };
        let v = serde_json::Value::Object(obj.clone());

        let Some(file_path) = payload_get_str(&v, "file_path") else {
            continue;
        };
        let detector = payload_get_str(&v, "detector_type")
            .or_else(|| payload_get_str(&v, "detector"))
            .or_else(|| payload_get_str(&v, "detected_ai_usage"))
            .unwrap_or_else(|| "unknown".to_string());
        let Some(confidence) = payload_get_num(&v, "confidence") else {
            continue;
        };

        // Exact matched pattern is not currently stored (Python discovery uses high-level evidence),
        // so keep it null unless explicitly present in the stored payload.
        let matched_pattern = payload_get_str(&v, "matched_pattern");

        // Stable, deterministic hash derived from stored fields only.
        // (Avoid serializing maps where key order can differ.)
        let hash_input = format!(
            "file_path={}\ndetector={}\nconfidence={:.12}\nmatched_pattern={}",
            file_path,
            detector,
            confidence,
            matched_pattern.as_deref().unwrap_or("")
        );
        let hash = sha256_hex_str(&hash_input);

        out.push(DiscoveryFindingOut {
            file_path,
            detector,
            confidence,
            matched_pattern,
            hash,
        });
    }

    // Deterministic ordering contract for auditors/consumers.
    out.sort_by(|a, b| {
        a.file_path
            .cmp(&b.file_path)
            .then_with(|| a.detector.cmp(&b.detector))
            .then_with(|| {
                a.confidence
                    .partial_cmp(&b.confidence)
                    .unwrap_or(Ordering::Equal)
            })
            .then_with(|| a.hash.cmp(&b.hash))
    });

    out
}

/// Machine-readable audit export: metadata, chain hashes, bundle digest, decision extracts, and timestamps.
/// Uses `bundle::bundle_document_value` and `bundle::bundle_sha256` (same as `/bundle` and `/bundle-hash`).
/// Ledger tenant follows API key mapping (`GOVAI_API_KEYS_JSON`); `X-GovAI-Project` is metering/metadata, not tenant isolation.
async fn export_run_route(
    State(audit): State<AuditState>,
    headers: HeaderMap,
    Path(run_id): Path<String>,
) -> (StatusCode, Json<serde_json::Value>) {
    let run_id = run_id.trim().to_string();
    if run_id.is_empty() {
        return api_err(
            StatusCode::BAD_REQUEST,
            "RUN_ID_REQUIRED",
            "Missing required path parameter run_id.",
            "Provide a non-empty `run_id` path segment.",
            None,
            Some(audit.policy_version),
            None,
        );
    }

    let (log_path, _) = match tenant_log_path(&audit, &headers) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("export_run_route: tenant_log_path: {e}");
            return api_err(
                StatusCode::BAD_REQUEST,
                "MISSING_TENANT_CONTEXT",
                "Missing tenant context.",
                "Provide `Authorization: Bearer <api_key>`.",
                None,
                Some(audit.policy_version),
                None,
            );
        }
    };
    let ledger_tenant_id =
        match project::require_tenant_id_for_ledger(&headers, audit.deployment_env) {
            Ok(t) => t,
            Err(e) => {
                eprintln!("export_run_route: require_tenant_id_for_ledger: {e}");
                return api_err(
                    StatusCode::BAD_REQUEST,
                    "MISSING_TENANT_CONTEXT",
                    "Missing tenant context.",
                    "Provide `Authorization: Bearer <api_key>`.",
                    None,
                    Some(audit.policy_version),
                    None,
                );
            }
        };
    let billing_tenant_id = project::billing_tenant_id(&headers);

    let events = match bundle::collect_events_for_run(&log_path, &run_id) {
        Ok(e) => e,
        Err(e) => {
            eprintln!("export_run_route: collect_events_for_run: {e}");
            return api_err(
                StatusCode::SERVICE_UNAVAILABLE,
                "EXPORT_NOT_AVAILABLE",
                "export not available",
                "Retry in a moment. If this persists, contact support.",
                Some(json!({ "run_id": run_id })),
                Some(audit.policy_version),
                None,
            );
        }
    };
    if events.is_empty() {
        return api_err(
            StatusCode::NOT_FOUND,
            "RUN_NOT_FOUND",
            "No events were found for this run_id in the current tenant ledger.",
            tenant_scoped_not_found_hint(),
            None,
            Some(audit.policy_version),
            Some(json!({ "run_id": run_id })),
        );
    }

    let events = bundle::canonicalize_evidence_events(events);
    let log_path_report = format!("rust/{}", log_path);
    let bundle_doc =
        bundle::bundle_document_value(&run_id, audit.policy_version, &log_path_report, &events);
    let artifact_path = bundle::find_model_artifact_path(&events);
    let bundle_sha256 = bundle::bundle_sha256(
        &run_id,
        audit.policy_version,
        &log_path_report,
        artifact_path.as_deref(),
        &events,
    );
    let events_content_sha256 = bundle::portable_evidence_digest_v1(&run_id, &events);

    // Explicit integrity anchor: persist a checkpoint of the full tenant ledger digest.
    let latest_checkpoint = match crate::audit_store::ensure_checkpoint_current(&log_path) {
        Ok(cp) => cp,
        Err(e) => {
            eprintln!("export_run_route: ensure_checkpoint_current: {e}");
            return api_err(
                StatusCode::SERVICE_UNAVAILABLE,
                "CHECKPOINT_NOT_AVAILABLE",
                "export not available",
                "Retry in a moment. If this persists, contact support.",
                Some(json!({ "raw": e, "run_id": run_id })),
                Some(audit.policy_version),
                None,
            );
        }
    };

    let chain_records = match crate::audit_store::collect_stored_records_for_run(&log_path, &run_id)
    {
        Ok(r) => r,
        Err(e) => {
            eprintln!("export_run_route: collect_stored_records_for_run: {e}");
            return api_err(
                StatusCode::SERVICE_UNAVAILABLE,
                "EXPORT_NOT_AVAILABLE",
                "export not available",
                "Retry in a moment. If this persists, contact support.",
                Some(json!({ "run_id": run_id })),
                Some(audit.policy_version),
                None,
            );
        }
    };

    let head_sha256 = chain_records.last().map(|r| r.record_hash.clone());
    let log_chain: Vec<serde_json::Value> = chain_records
        .iter()
        .filter_map(|rec| {
            let ev: Result<crate::schema::EvidenceEvent, _> = serde_json::from_str(&rec.event_json);
            let ev = ev.ok()?;
            Some(json!({
                "event_id": ev.event_id,
                "ts_utc": ev.ts_utc,
                "event_type": ev.event_type,
                "prev_hash": rec.prev_hash,
                "record_hash": rec.record_hash
            }))
        })
        .collect();

    let first_ts = events.first().map(|e| e.ts_utc.clone());
    let last_ts = events.last().map(|e| e.ts_utc.clone());

    let human = bundle_doc
        .get("human_approval")
        .cloned()
        .unwrap_or(serde_json::Value::Null);
    let human_ts = human
        .get("ts_utc")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let promo = bundle_doc
        .get("promotion")
        .cloned()
        .unwrap_or(serde_json::Value::Null);
    let promo_ts = promo
        .get("ts_utc")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    let eval_passed = bundle_doc
        .get("evaluation")
        .and_then(|e| e.get("passed"))
        .and_then(|v| v.as_bool());

    let derived = projection::derive_current_state_from_events_with_context(
        &run_id,
        &events,
        Some(bundle_sha256.clone()),
        last_ts.clone(),
    );
    let verdict = compliance_verdict_from_state(&derived);
    let blocked_reasons = blocked_reasons_from_state(&derived);

    let discovery_findings = extract_discovery_findings(&events)
        .into_iter()
        .map(|f| {
            json!({
                "file_path": f.file_path,
                "detector": f.detector,
                "confidence": f.confidence,
                "matched_pattern": f.matched_pattern,
                "hash": f.hash,
            })
        })
        .collect::<Vec<_>>();

    let out = json!({
        "ok": true,
        "schema_version": "aigov.audit_export.v1",
        "policy_version": audit.policy_version,
        "environment": audit.deployment_env.as_str(),
        // Deterministic: derived from ledger content, not server clock.
        "exported_at_utc": last_ts,
        "tenant": {
            "ledger_tenant_id": ledger_tenant_id,
            "billing_tenant_id": billing_tenant_id
        },
        "run": {
            "run_id": run_id,
            "policy_version": audit.policy_version,
            "log_path": log_path_report,
            "model_artifact_path": bundle_doc.get("model_artifact_path").cloned().unwrap_or(serde_json::Value::Null),
            "identifiers": bundle_doc.get("identifiers").cloned().unwrap_or(serde_json::Value::Null)
        },
        "discovery": {
            "findings": derived.discovery,
            "required_evidence": derived.requirements.required,
            "required_requirements": derived.requirements.required_requirements,
        },
        // Additive: file-level discovery evidence surfaced for auditors.
        // Deterministic ordering; derived only from the stored `ai_discovery_reported` payload.
        "discovery_findings": discovery_findings,
        "evidence_hashes": {
            "bundle_sha256": bundle_sha256,
            "events_content_sha256": events_content_sha256,
            "evidence_digest_schema": "aigov.evidence_digest.v1",
            "ledger_checkpoint": latest_checkpoint,
            "chain_head_record_sha256": head_sha256,
            "log_chain": log_chain
        },
        "decision": {
            "human_approval": human,
            "promotion": promo,
            "evaluation_passed": eval_passed,
            "verdict": verdict,
            "blocked_reasons": blocked_reasons
        },
        "evidence_requirements": {
            "required_evidence": derived.requirements.required,
            "provided_evidence": derived.requirements.satisfied,
            "missing_evidence": derived.requirements.missing,
            "required_requirements": derived.requirements.required_requirements,
            "provided_requirements": derived.requirements.satisfied_requirements,
            "missing_requirements": derived.requirements.missing_requirements
        },
        "evidence_events": bundle_doc.get("events").cloned().unwrap_or(serde_json::Value::Null),
        "timestamps": {
            "first_event_ts_utc": first_ts,
            "last_event_ts_utc": derived.evidence.latest_event_ts_utc,
            "human_approval_ts_utc": human_ts,
            "promotion_ts_utc": promo_ts
        }
    });

    if audit.metering.enabled {
        let key_hash = match audit_api_key::raw_bearer_token(&headers) {
            None => {
                return api_err(
                    StatusCode::UNAUTHORIZED,
                    "MISSING_API_KEY",
                    "Missing API key.",
                    "Provide `Authorization: Bearer <api_key>`.",
                    None,
                    None,
                    None,
                );
            }
            Some(t) => key_fingerprint(t),
        };
        let team_id = match metering::team_id_for_key_hash(&audit.pool, &key_hash).await {
            Ok(t) => t,
            Err(e) => {
                eprintln!("export_run_route: team_id_for_key_hash: {e}");
                return api_err(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "METERING_ERROR",
                    "We could not load metering information for this API key.",
                    "Retry in a moment. If this persists, contact support (this is a server-side issue).",
                    None,
                    Some(audit.policy_version),
                    None,
                );
            }
        };
        if let Some(team_id) = team_id {
            let ym = metering::year_month_utc_now();
            let _ = metering::increment_team_op_counter(
                &audit.pool,
                team_id,
                ym,
                metering::TeamOpCounter::Export,
            )
            .await;
        }
    } else {
        let tenant_id = project::billing_tenant_id(&headers);
        let _ = evidence_usage::increment_export_usage(&audit.pool, &tenant_id).await;
    }

    let _ = stripe_billing::record_usage_attribution(
        &audit.pool,
        &ledger_tenant_id,
        stripe_billing::BILLING_UNIT_AUDIT_EXPORT,
        &run_id,
        Some(verdict),
    )
    .await;

    let _ = crate::product_ops::try_record_first_milestone(
        &audit.pool,
        &ledger_tenant_id,
        "first_export",
        Some(run_id.as_str()),
        json!({}),
    )
    .await;
    let _ = crate::product_ops::recompute_tenant_health(&audit.pool, &ledger_tenant_id).await;

    (StatusCode::OK, Json(out))
}

async fn bundle_hash_route(
    State(audit): State<AuditState>,
    headers: HeaderMap,
    Query(q): Query<BundleHashQuery>,
) -> (StatusCode, Json<serde_json::Value>) {
    let (log_path, _) = match tenant_log_path(&audit, &headers) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("bundle_hash_route: tenant_log_path: {e}");
            return api_err(
                StatusCode::BAD_REQUEST,
                "MISSING_TENANT_CONTEXT",
                "Missing tenant context.",
                "Provide `Authorization: Bearer <api_key>`.",
                None,
                Some(audit.policy_version),
                None,
            );
        }
    };
    match bundle::collect_events_for_run(&log_path, &q.run_id) {
        Ok(events) => {
            if events.is_empty() {
                return api_err(
                    StatusCode::NOT_FOUND,
                    "RUN_NOT_FOUND",
                    "No events were found for this run_id in the current tenant ledger.",
                    tenant_scoped_not_found_hint(),
                    None,
                    Some(audit.policy_version),
                    Some(json!({ "run_id": q.run_id })),
                );
            }
            let events = bundle::canonicalize_evidence_events(events);
            let artifact_path = bundle::find_model_artifact_path(&events);
            let lp = format!("rust/{}", log_path);

            let digest = bundle::bundle_sha256(
                &q.run_id,
                audit.policy_version,
                &lp,
                artifact_path.as_deref(),
                &events,
            );
            let events_content_sha256 = bundle::portable_evidence_digest_v1(&q.run_id, &events);

            (
                StatusCode::OK,
                Json(json!({
                    "ok": true,
                    "run_id": q.run_id,
                    "policy_version": audit.policy_version,
                    "bundle_sha256": digest,
                    "events_content_sha256": events_content_sha256,
                    "evidence_digest_schema": "aigov.evidence_digest.v1"
                })),
            )
        }
        Err(e) => {
            eprintln!("bundle_hash_route: collect_events_for_run: {e}");
            api_err(
                StatusCode::SERVICE_UNAVAILABLE,
                "BUNDLE_NOT_AVAILABLE",
                "bundle not available",
                "Retry in a moment. If this persists, contact support.",
                Some(json!({ "run_id": q.run_id })),
                Some(audit.policy_version),
                None,
            )
        }
    }
}

async fn verify_log(
    State(audit): State<AuditState>,
    headers: HeaderMap,
) -> (StatusCode, Json<serde_json::Value>) {
    let (log_path, _) = match tenant_log_path(&audit, &headers) {
        Ok(p) => p,
        Err(e) => {
            return api_err(
                StatusCode::BAD_REQUEST,
                "MISSING_TENANT_CONTEXT",
                "Missing tenant context.",
                "Provide `Authorization: Bearer <api_key>`.",
                Some(serde_json::Value::String(e)),
                Some(audit.policy_version),
                None,
            );
        }
    };
    match verify_chain::verify_chain(&log_path) {
        Ok(_) => (StatusCode::OK, Json(json!({ "ok": true }))),
        Err(e) => api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "CHAIN_INVALID",
            "The append-only chain failed verification. The ledger may have been corrupted.",
            "Retry later. If this persists, contact support (this is a server-side integrity issue).",
            Some(json!({ "raw": e })),
            Some(audit.policy_version),
            None,
        ),
    }
}

/// Readiness: DB reachable, migrations complete, ledger writable (`GOVAI_LEDGER_DIR` or dev cwd).
async fn readiness_check(State(audit): State<AuditState>) -> (StatusCode, Json<serde_json::Value>) {
    if let Err(e) = sqlx::query("SELECT 1").fetch_one(&audit.pool).await {
        eprintln!("readiness: database_ping failed: {e}");
        crate::runtime_metrics::set_readiness_ready(false);
        crate::ops_log::readiness_failure_category("database_ping", &e.to_string());
        return api_error(
            StatusCode::SERVICE_UNAVAILABLE,
            "NOT_READY",
            "database not ready",
            "Verify Postgres connectivity and DATABASE_URL / GOVAI_DATABASE_URL.",
            Some(json!({ "checks": { "database_ping": false } })),
        );
    }

    if let Err(e) = db::verify_sqlx_migrations_complete(&audit.pool).await {
        eprintln!("readiness: migrations incomplete: {e}");
        crate::runtime_metrics::set_readiness_ready(false);
        crate::ops_log::readiness_failure_category("migrations_incomplete", &e.to_string());
        return api_error(
            StatusCode::SERVICE_UNAVAILABLE,
            "NOT_READY",
            "database not ready",
            "Apply migrations or enable GOVAI_AUTO_MIGRATE=true for automatic apply.",
            Some(json!({ "checks": { "migrations_complete": false } })),
        );
    }

    let ledger_err = match audit.deployment_env {
        GovaiEnvironment::Staging | GovaiEnvironment::Prod => {
            let Some(dir) = ledger_storage::configured_ledger_dir() else {
                crate::runtime_metrics::set_readiness_ready(false);
                crate::ops_log::readiness_failure_category(
                    "ledger_dir_missing",
                    "GOVAI_LEDGER_DIR missing in staging/prod",
                );
                return api_error(
                    StatusCode::SERVICE_UNAVAILABLE,
                    "NOT_READY",
                    "ledger not ready",
                    "Set GOVAI_LEDGER_DIR to a writable directory backed by persistent storage.",
                    Some(json!({ "checks": { "ledger_writable": false } })),
                );
            };
            ledger_storage::validate_ledger_dir(dir.as_path())
        }
        GovaiEnvironment::Dev => match ledger_storage::configured_ledger_dir() {
            Some(dir) => ledger_storage::validate_ledger_dir(dir.as_path()),
            None => std::env::current_dir()
                .map_err(|e| format!("cannot read cwd: {}", e))
                .and_then(|cwd| ledger_storage::validate_ledger_dir(&cwd)),
        },
    };

    if let Err(e) = ledger_err {
        eprintln!("readiness: ledger not writable: {e}");
        crate::runtime_metrics::set_readiness_ready(false);
        crate::ops_log::readiness_failure_category("ledger_not_writable", &e);
        return api_error(
            StatusCode::SERVICE_UNAVAILABLE,
            "NOT_READY",
            "ledger not ready",
            "Ensure GOVAI_LEDGER_DIR exists and is writable (or cwd writable in dev).",
            Some(json!({ "checks": { "ledger_writable": false } })),
        );
    }

    // `/ready` must reflect the same effective ledger semantics as `/evidence` append:
    // - tenant-scoped ledger filename resolution (`project::resolve_ledger_path`)
    // - parent directory existence (CI/container paths may exist at startup but differ at runtime)
    // - ability to create/open the tenant-scoped ledger file itself
    //
    // This intentionally does *not* rely on request headers (readiness is unauthenticated),
    // but it uses the same tenant-scoping naming scheme to catch path issues early.
    let pid = std::process::id();
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let probe_tenant = format!("ready-probe-{pid}-{nanos}");
    // Test override to deterministically exercise failure paths without changing production semantics.
    //
    // NOTE: `#[cfg(test)]` does NOT apply to integration tests (`rust/tests/*.rs`) because the
    // library is compiled as a normal dependency. Use `debug_assertions` so `cargo test` builds
    // (including CI) can enable the override, while release builds cannot.
    let probe_path_override: Option<String> = {
        #[cfg(any(test, debug_assertions))]
        {
            // Never allow the override outside of dev semantics.
            if matches!(audit.deployment_env, GovaiEnvironment::Dev) {
                std::env::var("GOVAI_TEST_READY_TENANT_PROBE_PATH")
                    .ok()
                    .map(|s| s.trim().to_string())
                    .filter(|s| !s.is_empty())
            } else {
                None
            }
        }
        #[cfg(not(any(test, debug_assertions)))]
        {
            None
        }
    };

    let probe_path = probe_path_override
        .unwrap_or_else(|| project::resolve_ledger_path(audit.ledger_base, &probe_tenant));
    eprintln!(
        "readiness: tenant_ledger_probe path={} ledger_base={} env={} ledger_dir={}",
        probe_path,
        audit.ledger_base,
        audit.deployment_env.as_str(),
        crate::ledger_storage::configured_ledger_dir()
            .map(|p| p.display().to_string())
            .unwrap_or_else(|| "(unset)".to_string())
    );
    if let Some(parent) = std::path::Path::new(&probe_path).parent() {
        if !parent.as_os_str().is_empty() && parent != std::path::Path::new(".") {
            if let Err(e) = std::fs::create_dir_all(parent) {
                let msg = format!(
                    "Failed to create tenant ledger parent directory {}: {e}",
                    parent.display()
                );
                eprintln!("readiness: tenant_ledger_probe_parent failed: {msg}");
                crate::runtime_metrics::set_readiness_ready(false);
                crate::ops_log::readiness_failure_category("tenant_ledger_probe_parent", &msg);
                return api_error(
                    StatusCode::SERVICE_UNAVAILABLE,
                    "NOT_READY",
                    "ledger not ready",
                    "Ensure GOVAI_LEDGER_DIR exists and is writable (or cwd writable in dev).",
                    Some(
                        json!({ "checks": { "tenant_ledger_probe": false }, "details": { "probe_path": probe_path, "raw": msg } }),
                    ),
                );
            }
        }
    }
    match std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&probe_path)
    {
        Ok(mut f) => {
            // Minimal write to ensure the filesystem path is usable for append semantics.
            if let Err(e) = std::io::Write::write_all(&mut f, b"") {
                let msg = format!("tenant ledger probe write failed: {e}");
                eprintln!("readiness: tenant_ledger_probe_write failed: {msg}");
                crate::runtime_metrics::set_readiness_ready(false);
                crate::ops_log::readiness_failure_category("tenant_ledger_probe_write", &msg);
                return api_error(
                    StatusCode::SERVICE_UNAVAILABLE,
                    "NOT_READY",
                    "ledger not ready",
                    "Ensure GOVAI_LEDGER_DIR exists and is writable (or cwd writable in dev).",
                    Some(
                        json!({ "checks": { "tenant_ledger_probe": false }, "details": { "probe_path": probe_path, "raw": msg } }),
                    ),
                );
            }
            // Best-effort cleanup; ignore failure.
            let _ = std::fs::remove_file(&probe_path);
        }
        Err(e) => {
            let msg = format!("tenant ledger probe open failed: {e}");
            eprintln!("readiness: tenant_ledger_probe_open failed: {msg}");
            crate::runtime_metrics::set_readiness_ready(false);
            crate::ops_log::readiness_failure_category("tenant_ledger_probe_open", &msg);
            return api_error(
                StatusCode::SERVICE_UNAVAILABLE,
                "NOT_READY",
                "ledger not ready",
                "Ensure GOVAI_LEDGER_DIR exists and is writable (or cwd writable in dev).",
                Some(
                    json!({ "checks": { "tenant_ledger_probe": false }, "details": { "probe_path": probe_path, "raw": msg } }),
                ),
            );
        }
    }

    let gov_enf = GovernanceEnforcementMode::from_env();
    let allow_nonempty = !governance_enforcement_tenant_allowlist_from_env().is_empty();
    crate::runtime_metrics::set_readiness_ready(true);
    (
        StatusCode::OK,
        Json(json!({
            "ok": true,
            "ready": true,
            "checks": {
                "database_ping": true,
                "migrations_complete": true,
                "ledger_writable": true,
                "tenant_ledger_probe": true
            },
            "runtime_governance_enforcement": runtime_governance_enforcement_diag(gov_enf, allow_nonempty)
        })),
    )
}

#[derive(Deserialize)]
struct BillingUsageSummaryQuery {
    /// RFC3339 inclusive lower bound (default: first instant of current UTC month).
    #[serde(default)]
    from: Option<String>,
    /// RFC3339 exclusive upper bound (default: now).
    #[serde(default)]
    to: Option<String>,
    /// e.g. `evidence_event`
    #[serde(default = "default_billing_unit_param")]
    unit: String,
}

fn default_billing_unit_param() -> String {
    "evidence_event".to_string()
}

async fn billing_usage_summary_route(
    State(audit): State<AuditState>,
    headers: HeaderMap,
    Query(q): Query<BillingUsageSummaryQuery>,
) -> (StatusCode, Json<serde_json::Value>) {
    let ledger_tid = match project::require_tenant_id_for_ledger(&headers, audit.deployment_env) {
        Ok(t) => t,
        Err(e) => {
            return api_err(
                StatusCode::BAD_REQUEST,
                "MISSING_TENANT_CONTEXT",
                "Missing tenant context.",
                "Provide `Authorization: Bearer <api_key>`.",
                Some(serde_json::Value::String(e)),
                Some(audit.policy_version),
                None,
            );
        }
    };

    let window_end = match q.to.as_deref() {
        Some(s) => match DateTime::parse_from_rfc3339(s) {
            Ok(d) => d.with_timezone(&Utc),
            Err(_) => {
                return api_err(
                    StatusCode::BAD_REQUEST,
                    "INVALID_QUERY",
                    "Invalid `to` timestamp (expected RFC3339).",
                    "Use an ISO-8601 / RFC3339 instant, e.g. 2026-05-01T00:00:00Z.",
                    None,
                    Some(audit.policy_version),
                    None,
                );
            }
        },
        None => Utc::now(),
    };

    let window_start = match q.from.as_deref() {
        Some(s) => match DateTime::parse_from_rfc3339(s) {
            Ok(d) => d.with_timezone(&Utc),
            Err(_) => {
                return api_err(
                    StatusCode::BAD_REQUEST,
                    "INVALID_QUERY",
                    "Invalid `from` timestamp (expected RFC3339).",
                    "Use an ISO-8601 / RFC3339 instant, e.g. 2026-05-01T00:00:00Z.",
                    None,
                    Some(audit.policy_version),
                    None,
                );
            }
        },
        None => Utc
            .with_ymd_and_hms(window_end.year(), window_end.month(), 1, 0, 0, 0)
            .single()
            .unwrap_or_else(Utc::now),
    };

    if window_start >= window_end {
        return api_err(
            StatusCode::BAD_REQUEST,
            "INVALID_QUERY",
            "`from` must be strictly before `to`.",
            "Widen the window or fix the bounds.",
            None,
            Some(audit.policy_version),
            None,
        );
    }

    let unit = {
        let u = q.unit.trim();
        if u.is_empty() {
            "evidence_event"
        } else {
            u
        }
    };
    match billing_trace::usage_summary_for_tenant(
        &audit.pool,
        &ledger_tid,
        unit,
        window_start,
        window_end,
    )
    .await
    {
        Ok(s) => (
            StatusCode::OK,
            Json(json!({
                "ok": true,
                "tenant_id": s.tenant_id,
                "billing_unit": s.billing_unit,
                "usage_count": s.count,
                "time_window": {
                    "start": s.window_start.to_rfc3339(),
                    "end": s.window_end.to_rfc3339()
                },
                "traces": s.traces.iter().map(|t| json!({
                    "tenant_id": t.tenant_id,
                    "run_id": t.run_id,
                    "occurred_at": t.occurred_at.to_rfc3339()
                })).collect::<Vec<_>>()
            })),
        ),
        Err(e) => api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "DB_ERROR",
            "Could not load billing usage summary.",
            "Retry in a moment. If this persists, contact support.",
            Some(json!({ "raw": e.to_string() })),
            Some(audit.policy_version),
            None,
        ),
    }
}

#[derive(Deserialize)]
struct BillingCheckoutRequest {
    /// When omitted, server uses `GOVAI_STRIPE_PRICE_PRO` (or legacy `GOVAI_STRIPE_PRICE_TEAM`).
    #[serde(default)]
    price_id: Option<String>,
    success_url: String,
    cancel_url: String,
}

#[derive(Deserialize)]
struct BillingReportUsageBody {
    #[serde(default = "default_report_usage_unit")]
    billing_unit: String,
}

fn default_report_usage_unit() -> String {
    stripe_billing::BILLING_UNIT_EVIDENCE_EVENT.to_string()
}

#[derive(Deserialize)]
struct BillingPortalBody {
    return_url: String,
}

#[derive(Deserialize)]
struct BillingReconciliationQuery {
    from: String,
    to: String,
    billing_unit: Option<String>,
}

async fn billing_checkout_session_route(
    State(audit): State<AuditState>,
    headers: HeaderMap,
    Json(body): Json<BillingCheckoutRequest>,
) -> (StatusCode, Json<serde_json::Value>) {
    let tenant_id =
        match stripe_billing::ledger_tenant_for_billing_headers(&headers, audit.deployment_env) {
            Ok(t) => t,
            Err(_) => {
                return api_err(
                    StatusCode::UNAUTHORIZED,
                    "MISSING_API_KEY",
                    "Missing API key.",
                    "Provide `Authorization: Bearer <api_key>`.",
                    None,
                    Some(audit.policy_version),
                    None,
                );
            }
        };
    let sk = match stripe_billing::stripe_secret_key() {
        Ok(s) => s,
        Err(msg) => {
            return api_err(
                StatusCode::SERVICE_UNAVAILABLE,
                "STRIPE_NOT_CONFIGURED",
                "Stripe API is not configured on this server.",
                "Set GOVAI_STRIPE_SECRET_KEY to your Stripe secret key (sk_live_… or sk_test_…).",
                Some(json!({ "detail": msg })),
                Some(audit.policy_version),
                None,
            );
        }
    };
    let price = match body
        .price_id
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
    {
        Some(p) => p.to_string(),
        None => match stripe_billing::default_pro_checkout_price_id() {
            Ok(p) => p,
            Err(msg) => {
                return api_err(
                    StatusCode::SERVICE_UNAVAILABLE,
                    "STRIPE_PRICE_NOT_CONFIGURED",
                    "Pro checkout price is not configured on this server.",
                    "Set GOVAI_STRIPE_PRICE_PRO to your Stripe Pro subscription Price id (price_…), or pass price_id in the request body.",
                    Some(json!({ "detail": msg })),
                    Some(audit.policy_version),
                    None,
                );
            }
        },
    };
    if !price.starts_with("price_") {
        return api_err(
            StatusCode::BAD_REQUEST,
            "INVALID_PRICE_ID",
            "price_id must be a Stripe Price id (price_…).",
            "Pass a subscription recurring price from the Stripe Dashboard.",
            None,
            Some(audit.policy_version),
            None,
        );
    }
    if body.success_url.trim().is_empty() || body.cancel_url.trim().is_empty() {
        return api_err(
            StatusCode::BAD_REQUEST,
            "INVALID_URL",
            "success_url and cancel_url must be non-empty absolute URLs.",
            "Provide https://… URLs where Stripe should redirect after checkout.",
            None,
            Some(audit.policy_version),
            None,
        );
    }
    match stripe_billing::stripe_create_checkout_session(
        &sk,
        price.as_str(),
        body.success_url.trim(),
        body.cancel_url.trim(),
        &tenant_id,
    )
    .await
    {
        Ok((session_id, checkout_url)) => (
            StatusCode::OK,
            Json(json!({
                "ok": true,
                "tenant_id": tenant_id,
                "session_id": session_id,
                "checkout_url": checkout_url,
            })),
        ),
        Err(e) => api_err(
            StatusCode::BAD_GATEWAY,
            "STRIPE_CHECKOUT_FAILED",
            "Stripe refused or failed to create the Checkout Session.",
            "Verify price_id, account mode (test vs live), and Stripe logs; then retry.",
            Some(json!({ "detail": e })),
            Some(audit.policy_version),
            None,
        ),
    }
}

async fn billing_status_route(
    State(audit): State<AuditState>,
    headers: HeaderMap,
) -> (StatusCode, Json<serde_json::Value>) {
    let tenant =
        match stripe_billing::ledger_tenant_for_billing_headers(&headers, audit.deployment_env) {
            Ok(t) => t,
            Err(_) => {
                return api_err(
                    StatusCode::UNAUTHORIZED,
                    "MISSING_API_KEY",
                    "Missing API key.",
                    "Provide `Authorization: Bearer <api_key>`.",
                    None,
                    Some(audit.policy_version),
                    None,
                );
            }
        };
    match stripe_billing::billing_status_for_tenant(&audit.pool, &tenant).await {
        Ok(j) => {
            let mut v = serde_json::to_value(&j).unwrap_or_else(|_| json!({}));
            if let Some(obj) = v.as_object_mut() {
                obj.insert("ok".to_string(), json!(true));
                obj.insert(
                    "enforcement_enabled".to_string(),
                    json!(stripe_billing::billing_enforcement_enabled()),
                );
                obj.insert(
                    "pro_list_price_monthly".to_string(),
                    json!(pricing::PRO_LIST_PRICE_EUR_MONTHLY),
                );
                obj.insert(
                    "stripe_configured".to_string(),
                    json!(stripe_billing::stripe_secret_key().is_ok()),
                );
                obj.insert(
                    "stripe_checkout_configured".to_string(),
                    json!(stripe_billing::default_pro_checkout_price_id().is_ok()),
                );
            }
            (StatusCode::OK, Json(v))
        }
        Err(e) => api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "BILLING_STATUS_ERROR",
            "Could not load billing status.",
            "Retry in a moment. If this persists, contact support.",
            Some(json!({ "raw": e.to_string() })),
            Some(audit.policy_version),
            None,
        ),
    }
}

async fn billing_report_usage_route(
    State(audit): State<AuditState>,
    headers: HeaderMap,
    Json(body): Json<BillingReportUsageBody>,
) -> (StatusCode, Json<serde_json::Value>) {
    let tenant =
        match stripe_billing::ledger_tenant_for_billing_headers(&headers, audit.deployment_env) {
            Ok(t) => t,
            Err(_) => {
                return api_err(
                    StatusCode::UNAUTHORIZED,
                    "MISSING_API_KEY",
                    "Missing API key.",
                    "Provide `Authorization: Bearer <api_key>`.",
                    None,
                    Some(audit.policy_version),
                    None,
                );
            }
        };
    let unit = body.billing_unit.trim();
    if unit.is_empty() || !stripe_billing::ALL_BILLING_UNITS.iter().any(|u| *u == unit) {
        return api_err(
            StatusCode::BAD_REQUEST,
            "INVALID_BILLING_UNIT",
            "Unknown billing_unit.",
            "Use one of: evidence_event, compliance_check, audit_export, discovery_scan.",
            None,
            Some(audit.policy_version),
            None,
        );
    }
    match stripe_billing::report_usage_for_tenant(&audit.pool, &tenant, unit).await {
        Ok(out) => (
            StatusCode::OK,
            Json(json!({
                "ok": true,
                "tenant_id": tenant,
                "billing_unit": unit,
                "idempotent_hit": out.idempotent_hit,
                "report_id": out.report_id,
                "quantity": out.quantity,
                "period_start": out.period_start,
                "period_end": out.period_end,
                "status": out.status,
                "stripe_usage_record_id": out.stripe_usage_record_id,
            })),
        ),
        Err(e) => api_err(
            StatusCode::BAD_GATEWAY,
            "STRIPE_USAGE_REPORT_FAILED",
            "Usage was recorded locally but reporting to Stripe failed.",
            "Fix Stripe configuration or subscription item id, then POST again (idempotent for the same period).",
            Some(json!({ "detail": e })),
            Some(audit.policy_version),
            None,
        ),
    }
}

async fn billing_portal_route(
    State(audit): State<AuditState>,
    headers: HeaderMap,
    Json(body): Json<BillingPortalBody>,
) -> (StatusCode, Json<serde_json::Value>) {
    let tenant =
        match stripe_billing::ledger_tenant_for_billing_headers(&headers, audit.deployment_env) {
            Ok(t) => t,
            Err(_) => {
                return api_err(
                    StatusCode::UNAUTHORIZED,
                    "MISSING_API_KEY",
                    "Missing API key.",
                    "Provide `Authorization: Bearer <api_key>`.",
                    None,
                    Some(audit.policy_version),
                    None,
                );
            }
        };
    if body.return_url.trim().is_empty() {
        return api_err(
            StatusCode::BAD_REQUEST,
            "INVALID_URL",
            "return_url must be a non-empty absolute URL.",
            "Provide an https://… URL where Stripe should return after the billing portal.",
            None,
            Some(audit.policy_version),
            None,
        );
    }
    let customer_id: Option<String> = match sqlx::query_scalar::<sqlx::Postgres, Option<String>>(
        r#"select stripe_customer_id from public.tenant_billing_accounts where tenant_id = $1"#,
    )
    .bind(&tenant)
    .fetch_optional(&audit.pool)
    .await
    {
        Ok(Some(inner)) => inner,
        Ok(None) | Err(_) => None,
    };
    let Some(customer_id) = customer_id.filter(|s| !s.trim().is_empty()) else {
        return api_err(
            StatusCode::NOT_FOUND,
            "BILLING_ACCOUNT_NOT_FOUND",
            "No Stripe customer is associated with this tenant.",
            "Create checkout session first.",
            None,
            Some(audit.policy_version),
            None,
        );
    };
    let secret = match stripe_billing::stripe_secret_key() {
        Ok(s) => s,
        Err(e) => {
            return api_err(
                StatusCode::SERVICE_UNAVAILABLE,
                "STRIPE_NOT_CONFIGURED",
                "Stripe is not configured on this server.",
                "Contact the operator to configure GOVAI_STRIPE_SECRET_KEY.",
                Some(json!({ "raw": e })),
                Some(audit.policy_version),
                None,
            );
        }
    };
    match stripe_billing::stripe_create_billing_portal_session(
        &secret,
        customer_id.trim(),
        body.return_url.trim(),
    )
    .await
    {
        Ok(url) => (
            StatusCode::OK,
            Json(json!({ "ok": true, "tenant_id": tenant, "portal_url": url })),
        ),
        Err(e) => api_err(
            StatusCode::BAD_GATEWAY,
            "STRIPE_PORTAL_FAILED",
            "Could not create billing portal session.",
            "Verify Stripe customer id and portal configuration.",
            Some(json!({ "raw": e })),
            Some(audit.policy_version),
            None,
        ),
    }
}

async fn billing_invoices_route(
    State(audit): State<AuditState>,
    headers: HeaderMap,
) -> (StatusCode, Json<serde_json::Value>) {
    let tenant =
        match stripe_billing::ledger_tenant_for_billing_headers(&headers, audit.deployment_env) {
            Ok(t) => t,
            Err(_) => {
                return api_err(
                    StatusCode::UNAUTHORIZED,
                    "MISSING_API_KEY",
                    "Missing API key.",
                    "Provide `Authorization: Bearer <api_key>`.",
                    None,
                    Some(audit.policy_version),
                    None,
                );
            }
        };
    let customer_id: Option<String> = match sqlx::query_scalar::<sqlx::Postgres, Option<String>>(
        r#"select stripe_customer_id from public.tenant_billing_accounts where tenant_id = $1"#,
    )
    .bind(&tenant)
    .fetch_optional(&audit.pool)
    .await
    {
        Ok(Some(inner)) => inner,
        Ok(None) | Err(_) => None,
    };
    let Some(customer_id) = customer_id.filter(|s| !s.trim().is_empty()) else {
        return api_err(
            StatusCode::NOT_FOUND,
            "BILLING_ACCOUNT_NOT_FOUND",
            "No Stripe customer is associated with this tenant.",
            "Create checkout session first.",
            None,
            Some(audit.policy_version),
            None,
        );
    };
    let secret = match stripe_billing::stripe_secret_key() {
        Ok(s) => s,
        Err(e) => {
            return api_err(
                StatusCode::SERVICE_UNAVAILABLE,
                "STRIPE_NOT_CONFIGURED",
                "Stripe is not configured on this server.",
                "Contact the operator to configure GOVAI_STRIPE_SECRET_KEY.",
                Some(json!({ "raw": e })),
                Some(audit.policy_version),
                None,
            );
        }
    };
    match stripe_billing::stripe_list_invoices(&secret, customer_id.trim(), 20).await {
        Ok(rows) => (
            StatusCode::OK,
            Json(json!({
                "ok": true,
                "tenant_id": tenant,
                "invoices": rows
            })),
        ),
        Err(e) => api_err(
            StatusCode::BAD_GATEWAY,
            "STRIPE_INVOICES_FAILED",
            "Could not list invoices from Stripe.",
            "Retry in a moment. If this persists, contact support.",
            Some(json!({ "raw": e })),
            Some(audit.policy_version),
            None,
        ),
    }
}

async fn billing_reconciliation_route(
    State(audit): State<AuditState>,
    headers: HeaderMap,
    Query(q): Query<BillingReconciliationQuery>,
) -> (StatusCode, Json<serde_json::Value>) {
    let tenant =
        match stripe_billing::ledger_tenant_for_billing_headers(&headers, audit.deployment_env) {
            Ok(t) => t,
            Err(_) => {
                return api_err(
                    StatusCode::UNAUTHORIZED,
                    "MISSING_API_KEY",
                    "Missing API key.",
                    "Provide `Authorization: Bearer <api_key>`.",
                    None,
                    Some(audit.policy_version),
                    None,
                );
            }
        };
    let from = match DateTime::parse_from_rfc3339(q.from.trim()) {
        Ok(d) => d.with_timezone(&Utc),
        Err(_) => {
            return api_err(
                StatusCode::BAD_REQUEST,
                "INVALID_FROM",
                "Query parameter `from` must be RFC3339.",
                "Example: 2026-05-01T00:00:00Z",
                None,
                Some(audit.policy_version),
                None,
            );
        }
    };
    let to = match DateTime::parse_from_rfc3339(q.to.trim()) {
        Ok(d) => d.with_timezone(&Utc),
        Err(_) => {
            return api_err(
                StatusCode::BAD_REQUEST,
                "INVALID_TO",
                "Query parameter `to` must be RFC3339.",
                "Example: 2026-05-31T23:59:59Z",
                None,
                Some(audit.policy_version),
                None,
            );
        }
    };
    if from >= to {
        return api_err(
            StatusCode::BAD_REQUEST,
            "INVALID_RANGE",
            "Parameter `from` must be before `to`.",
            "Adjust the time range and retry.",
            None,
            Some(audit.policy_version),
            None,
        );
    }
    if let Some(ref u) = q.billing_unit {
        let u = u.trim();
        if !u.is_empty() && !stripe_billing::ALL_BILLING_UNITS.iter().any(|x| *x == u) {
            return api_err(
                StatusCode::BAD_REQUEST,
                "INVALID_BILLING_UNIT",
                "Unknown billing_unit.",
                "Use one of: evidence_event, compliance_check, audit_export, discovery_scan.",
                None,
                Some(audit.policy_version),
                None,
            );
        }
    }
    let unit = q.billing_unit.as_deref().filter(|s| !s.trim().is_empty());
    match stripe_billing::reconciliation_for_tenant(&audit.pool, &tenant, from, to, unit).await {
        Ok(v) => (StatusCode::OK, Json(v)),
        Err(e) => api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "RECONCILIATION_ERROR",
            "Could not build reconciliation.",
            "Retry in a moment. If this persists, contact support.",
            Some(json!({ "raw": e.to_string() })),
            Some(audit.policy_version),
            None,
        ),
    }
}

async fn rate_limit_middleware(
    State(audit): State<AuditState>,
    request: Request,
    next: Next,
) -> axum::response::Response {
    // Only apply to gated audit routes (those already require API key), but enforce
    // fail-closed behavior if tenant context can't be established.
    let headers = request.headers().clone();
    if let Err(e) =
        crate::rate_limit::check_request_allowed_async(&audit.pool, &headers, audit.deployment_env)
            .await
    {
        return api_err(
            StatusCode::TOO_MANY_REQUESTS,
            "RATE_LIMITED",
            "Request rate limit exceeded.",
            "Retry later. If this persists, contact support.",
            Some(json!({ "raw": e })),
            Some(audit.policy_version),
            None,
        )
        .into_response();
    }
    next.run(request).await
}

pub fn audit_router(
    log_path: &'static str,
    policy_version: &'static str,
    deployment_env: GovaiEnvironment,
    policy_store: PolicyStore,
    api_usage: ApiUsageState,
    pool: DbPool,
    metering: MeteringConfig,
) -> Router {
    let pool_for_gate = pool.clone();
    let state = AuditState {
        ledger_base: log_path,
        policy_version,
        deployment_env,
        policy_store,
        pool,
        metering,
    };
    let api_key_cfg = crate::audit_api_key::AuditApiKeyConfig::from_env();
    let u = api_usage;
    let audit_key_layer = middleware::from_fn(move |request: Request, next: Next| {
        let cfg = api_key_cfg.clone();
        let usage = u.clone();
        let gate_pool = pool_for_gate.clone();
        async move {
            crate::audit_api_key::gate_audit_routes_with_state(
                axum::extract::State(crate::audit_api_key::AuditKeyGateState {
                    cfg,
                    usage,
                    pool: gate_pool,
                    deployment_env,
                }),
                request,
                next,
            )
            .await
        }
    });
    let billing_enforcement_layer =
        middleware::from_fn_with_state(state.clone(), billing_enforcement_middleware);
    let rate_limit_layer = middleware::from_fn_with_state(state.clone(), rate_limit_middleware);

    let unauthenticated = Router::new()
        .route("/ready", get(readiness_check))
        .route("/stripe/webhook", post(stripe_webhook_route))
        .with_state(state.clone());

    let gated = Router::new()
        .route("/evidence", post(ingest))
        .route("/usage", get(usage_route))
        .route("/billing/usage-summary", get(billing_usage_summary_route))
        .route(
            "/billing/checkout-session",
            post(billing_checkout_session_route),
        )
        .route("/billing/status", get(billing_status_route))
        .route("/billing/report-usage", post(billing_report_usage_route))
        // Phase 2 (M0) preview/stub: runtime governance check. Fail-closed by default.
        .route("/v1/runtime/evaluate", post(runtime_evaluate_route))
        .route("/verify", get(verify))
        .route("/verify-immutable", get(verify_immutable))
        .route("/bundle", get(bundle_route))
        .route("/bundle-hash", get(bundle_hash_route))
        .route("/verify-log", get(verify_log))
        .route("/compliance-summary", get(compliance_summary_route))
        .route("/api/export/:run_id", get(export_run_route))
        .route("/billing/portal-session", post(billing_portal_route))
        .route("/billing/invoices", get(billing_invoices_route))
        .route("/billing/reconciliation", get(billing_reconciliation_route))
        .layer(rate_limit_layer)
        .layer(billing_enforcement_layer)
        .layer(audit_key_layer)
        .with_state(state.clone());

    Router::new().merge(unauthenticated).merge(gated)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum RuntimeEvaluateMode {
    Disabled,
    Shadow,
}

impl RuntimeEvaluateMode {
    fn from_env(deployment_env: GovaiEnvironment) -> Self {
        // Preview/stub control: explicitly opt in for dev/shadow only.
        // Any unrecognized value => disabled (fail-closed).
        let raw = std::env::var("GOVAI_RUNTIME_EVALUATE").unwrap_or_default();
        let v = raw.trim().to_ascii_lowercase();
        match v.as_str() {
            "shadow" | "dev" | "on" | "true" | "1" if deployment_env == GovaiEnvironment::Dev => {
                RuntimeEvaluateMode::Shadow
            }
            _ => RuntimeEvaluateMode::Disabled,
        }
    }
}

/// Phase 3 M7.2: structured governance control evaluation (additive mapping only; does not drive verdict/enforcement).
#[derive(Debug, Clone, Copy, Serialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
enum RuntimeControlEvaluationStatus {
    Pass,
    Fail,
    Warn,
    #[allow(dead_code)]
    NotApplicable,
}

#[derive(Debug, Clone, Serialize)]
struct RuntimeControlEvaluation {
    control_id: String,
    status: RuntimeControlEvaluationStatus,
    source: String,
    reason_codes: Vec<String>,
}

/// Phase 4 M3: advisory-only capability policy shadow (does not participate in merge / verdict).
///
/// Requires non-empty `action` at the HTTP layer; callers pass `action_present` after validation.
fn capability_shadow_advisory_evaluations(
    action_present: bool,
    agent_capability_id: Option<&str>,
    delegation_context_present: bool,
    delegated_capability_id: Option<&str>,
) -> Vec<RuntimeControlEvaluation> {
    let agent_cap = agent_capability_id.map(str::trim).filter(|s| !s.is_empty());
    let del_cap = delegated_capability_id
        .map(str::trim)
        .filter(|s| !s.is_empty());

    let mut out = Vec::new();

    if action_present && agent_cap.is_some() {
        out.push(RuntimeControlEvaluation {
            control_id: "GOVAI.AGENT.CAPABILITY_DECLARED".into(),
            status: RuntimeControlEvaluationStatus::Pass,
            source: "capability_shadow".into(),
            reason_codes: vec![],
        });
    }

    if delegation_context_present {
        if let Some(d) = del_cap.as_deref() {
            let mismatch = match agent_cap.as_deref() {
                None => true,
                Some(a) => a != d,
            };
            if mismatch {
                out.push(RuntimeControlEvaluation {
                    control_id: "GOVAI.AGENT.CAPABILITY_DELEGATION_MISMATCH".into(),
                    status: RuntimeControlEvaluationStatus::Warn,
                    source: "capability_shadow".into(),
                    reason_codes: vec!["capability_delegation_mismatch".into()],
                });
            }
        } else if agent_cap.is_none() {
            out.push(RuntimeControlEvaluation {
                control_id: "GOVAI.AGENT.CAPABILITY_UNDECLARED".into(),
                status: RuntimeControlEvaluationStatus::Warn,
                source: "capability_shadow".into(),
                reason_codes: vec!["capability_undeclared".into()],
            });
        }
    }

    out
}

/// Deterministic reason-code → control mapping for the runtime evaluate stub (`runtime_mode` source only).
fn runtime_stub_control_evaluations(mode: RuntimeEvaluateMode) -> Vec<RuntimeControlEvaluation> {
    match mode {
        RuntimeEvaluateMode::Disabled => vec![RuntimeControlEvaluation {
            control_id: "GOVAI.RUNTIME.MODE_DISABLED".into(),
            status: RuntimeControlEvaluationStatus::Fail,
            source: "runtime_mode".into(),
            reason_codes: vec!["runtime_not_enabled".into()],
        }],
        RuntimeEvaluateMode::Shadow => vec![RuntimeControlEvaluation {
            control_id: "GOVAI.RUNTIME.SHADOW_MODE".into(),
            status: RuntimeControlEvaluationStatus::Warn,
            source: "runtime_mode".into(),
            reason_codes: vec!["shadow_mode_no_enforcement".into()],
        }],
    }
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RuntimeDatasetLineageRefInput {
    #[serde(default)]
    dataset_id: Option<String>,
    #[serde(default)]
    dataset_digest: Option<String>,
}

#[derive(Debug, Clone, serde::Deserialize, PartialEq, Eq, Copy)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
enum RuntimeRiskClass {
    Minimal,
    Limited,
    High,
    Prohibited,
}

impl Default for RuntimeRiskClass {
    fn default() -> Self {
        RuntimeRiskClass::Limited
    }
}

impl RuntimeRiskClass {
    fn parse_opt(o: Option<RuntimeRiskClass>) -> Self {
        o.unwrap_or_default()
    }
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RuntimeEvaluateRequest {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    correlation_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    action: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    artifact_digest: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    model_digest: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    deployment_digest: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    trace_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    request_fingerprint: Option<String>,
    /// Phase 3 M7.3: optional shadow/metadata-only lineage refs (`null`/omitted => empty).
    #[serde(default)]
    dataset_lineage_refs: Option<Vec<RuntimeDatasetLineageRefInput>>,
    /// Phase 3 M7.4: optional human override reference (`null`/omitted => null in response).
    #[serde(default)]
    override_ref: Option<RuntimeOverrideRefInput>,
    /// Phase 3 M7.x: optional dataset risk tier for lineage enforcement (default LIMITED).
    #[serde(default)]
    risk_class: Option<RuntimeRiskClass>,
    /// Phase 4 M1: optional actor identity metadata (`null`/omitted ⇒ null in responses/ledger).
    #[serde(default)]
    agent_context: Option<RuntimeAgentContextInput>,
    /// Phase 4 M2: optional delegation graph trace metadata (`null`/omitted ⇒ null in responses/ledger).
    #[serde(default)]
    delegation_context: Option<RuntimeDelegationContextInput>,
}

/// Phase 3 M7.3: dataset lineage fingerprint (validated metadata only; no raw content).
#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
struct RuntimeDatasetLineageRef {
    dataset_id: String,
    dataset_digest: String,
}

/// Phase 3 M7.4: human override pointer (shadow metadata only; does not authorize bypass).
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RuntimeOverrideRefInput {
    #[serde(default)]
    override_id: Option<String>,
    #[serde(default)]
    target_decision_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
struct RuntimeOverrideRef {
    override_id: String,
    target_decision_id: String,
}

/// Phase 4 M1: optional caller-supplied actor metadata (additive; no verdict/enforcement coupling).
#[derive(Default, Debug, Deserialize)]
#[serde(deny_unknown_fields, default)]
struct RuntimeAgentContextInput {
    #[serde(default)]
    agent_id: Option<String>,
    #[serde(default)]
    principal_id: Option<String>,
    #[serde(default)]
    delegation_id: Option<String>,
    #[serde(default)]
    capability_id: Option<String>,
}

#[derive(Default, Debug, Clone, Serialize, PartialEq, Eq)]
struct RuntimeAgentContext {
    #[serde(skip_serializing_if = "Option::is_none")]
    agent_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    principal_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    delegation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    capability_id: Option<String>,
}

/// Phase 4 M2: optional caller-supplied delegation edge metadata (additive; no verdict/enforcement coupling).
#[derive(Default, Debug, Deserialize)]
#[serde(deny_unknown_fields, default)]
struct RuntimeDelegationContextInput {
    #[serde(default)]
    delegation_id: Option<String>,
    #[serde(default)]
    parent_delegation_id: Option<String>,
    #[serde(default)]
    delegator_agent_id: Option<String>,
    #[serde(default)]
    delegatee_agent_id: Option<String>,
    #[serde(default)]
    delegated_capability_id: Option<String>,
    #[serde(default)]
    delegation_scope: Option<String>,
    #[serde(default)]
    expires_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
struct RuntimeDelegationContext {
    delegation_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    parent_delegation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    delegator_agent_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    delegatee_agent_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    delegated_capability_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    delegation_scope: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    expires_at: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum GovernanceEnforcementMode {
    Off,
    Shadow,
    Enforced,
}

impl GovernanceEnforcementMode {
    fn parse_env(raw: Option<String>) -> Self {
        let Some(s) = raw else {
            return Self::Off;
        };
        let v = s.trim().to_ascii_lowercase();
        match v.as_str() {
            "shadow" => Self::Shadow,
            "enforced" => Self::Enforced,
            "" | "off" => Self::Off,
            _ => Self::Off,
        }
    }

    fn from_env() -> Self {
        Self::parse_env(std::env::var("GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT").ok())
    }

    fn as_str(&self) -> &'static str {
        match self {
            Self::Off => "off",
            Self::Shadow => "shadow",
            Self::Enforced => "enforced",
        }
    }

    fn applies_lineage_governance(&self) -> bool {
        !matches!(self, Self::Off)
    }

    fn is_enforced_scope(&self) -> bool {
        matches!(self, Self::Enforced)
    }
}

fn governance_enforcement_tenant_allowlist_from_env() -> std::collections::HashSet<String> {
    std::env::var("GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT_TENANTS")
        .unwrap_or_default()
        .split(',')
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect()
}

fn runtime_primary_artifact_digest_for_governance<'a>(
    artifact: &'a Option<String>,
    model: &'a Option<String>,
    deployment: &'a Option<String>,
) -> Option<&'a str> {
    artifact
        .as_deref()
        .into_iter()
        .chain(model.as_deref())
        .chain(deployment.as_deref())
        .map(str::trim)
        .find(|s| !s.is_empty())
}

/// Operational diagnostics for readiness (no tenant headers; allowlist reflects env only).
fn runtime_governance_enforcement_diag(
    gov: GovernanceEnforcementMode,
    allowlist_nonempty: bool,
) -> serde_json::Value {
    let enforceable = gov == GovernanceEnforcementMode::Enforced && allowlist_nonempty;
    let reason_if_not_enforceable = if enforceable {
        serde_json::Value::Null
    } else if gov != GovernanceEnforcementMode::Enforced {
        serde_json::Value::String(
            "global_runtime_governance_enforcement_not_set_to_enforced".into(),
        )
    } else {
        serde_json::Value::String("tenant_allowlist_empty_or_required_for_enforced_mode".into())
    };
    json!({
        "mode": gov.as_str(),
        "configured_mode": gov.as_str(),
        "tenant_allowlist_configured": allowlist_nonempty,
        "enforceable": enforceable,
        "reason_if_not_enforceable": reason_if_not_enforceable,
    })
}

/// Global runtime governance + autonomy ingest flags for tenant-console snapshot.
pub fn tenant_console_runtime_enforcement_block() -> Value {
    let gov_enf = GovernanceEnforcementMode::from_env();
    let allow_nonempty = !governance_enforcement_tenant_allowlist_from_env().is_empty();
    json!({
        "global_mode": gov_enf.as_str(),
        "global_diagnostics": runtime_governance_enforcement_diag(gov_enf, allow_nonempty),
        "autonomy_ingest_enforcement_enabled": crate::autonomous_runtime::autonomy_enforcement_enabled_from_env(),
    })
}

/// Audit backend deployment identity for tenant-console snapshot (DB connectivity assumed ok when handler runs).
pub fn tenant_console_audit_backend_block(deployment_env: GovaiEnvironment) -> Value {
    json!({
        "connectivity": "ok",
        "deployment_environment": deployment_env.as_str(),
        "policy_version": crate::govai_environment::policy_version_for(deployment_env),
        "service": "govai_audit_backend",
        "authoritative_verdict_route": "GET /compliance-summary",
    })
}

fn governance_known_reason(reason: &str) -> bool {
    matches!(
        reason,
        "runtime_not_enabled"
            | "shadow_mode_no_enforcement"
            | "dataset_lineage_required"
            | "governance_context_incomplete"
            | "unknown_reason_code"
    )
}

fn runtime_risk_class_as_str(r: RuntimeRiskClass) -> &'static str {
    match r {
        RuntimeRiskClass::Minimal => "MINIMAL",
        RuntimeRiskClass::Limited => "LIMITED",
        RuntimeRiskClass::High => "HIGH",
        RuntimeRiskClass::Prohibited => "PROHIBITED",
    }
}

fn merge_runtime_governance_controls(
    stub: &[RuntimeControlEvaluation],
    gov_mode: GovernanceEnforcementMode,
    risk: RuntimeRiskClass,
    dataset_lineage_empty: bool,
    enforced_for_tenant: bool,
) -> Vec<RuntimeControlEvaluation> {
    let mut merged = stub.to_owned();
    if !gov_mode.applies_lineage_governance() {
        return merged;
    }
    if risk == RuntimeRiskClass::High && dataset_lineage_empty {
        if gov_mode.is_enforced_scope() && enforced_for_tenant {
            merged.push(RuntimeControlEvaluation {
                control_id: "GOVAI.DATASET.LINEAGE_REQUIRED".into(),
                status: RuntimeControlEvaluationStatus::Fail,
                source: "dataset_lineage_rule".into(),
                reason_codes: vec!["dataset_lineage_required".into()],
            });
        } else {
            merged.push(RuntimeControlEvaluation {
                control_id: "GOVAI.DATASET.LINEAGE_REQUIRED".into(),
                status: RuntimeControlEvaluationStatus::Warn,
                source: "dataset_lineage_rule".into(),
                reason_codes: vec!["dataset_lineage_required".into()],
            });
        }
    }
    merged
}

fn collect_unmapped_runtime_reason_codes(merged_base: &[RuntimeControlEvaluation]) -> bool {
    merged_base
        .iter()
        .flat_map(|c| c.reason_codes.iter())
        .any(|rc| {
            let t = rc.trim();
            !t.is_empty() && !governance_known_reason(t)
        })
}

fn unknown_reason_control(
    gov_mode: GovernanceEnforcementMode,
    enforced_hard: bool,
) -> Option<RuntimeControlEvaluation> {
    if gov_mode == GovernanceEnforcementMode::Off {
        return None;
    }
    Some(if gov_mode.is_enforced_scope() && enforced_hard {
        RuntimeControlEvaluation {
            control_id: "GOVAI.GOVERNANCE.REASON_MAPPING".into(),
            status: RuntimeControlEvaluationStatus::Fail,
            source: "reason_code_mapping".into(),
            reason_codes: vec!["unknown_reason_code".into()],
        }
    } else {
        RuntimeControlEvaluation {
            control_id: "GOVAI.GOVERNANCE.REASON_MAPPING".into(),
            status: RuntimeControlEvaluationStatus::Warn,
            source: "reason_code_mapping".into(),
            reason_codes: vec!["unknown_reason_code".into()],
        }
    })
}

fn summarize_merged_controls(merged: &[RuntimeControlEvaluation]) -> (&'static str, Vec<String>) {
    let mut reasons: Vec<String> = merged
        .iter()
        .flat_map(|c| c.reason_codes.iter().cloned())
        .collect::<std::collections::BTreeSet<_>>()
        .into_iter()
        .collect::<Vec<_>>();

    let fail_lineage_dataset = merged.iter().any(|c| {
        c.control_id == "GOVAI.DATASET.LINEAGE_REQUIRED"
            && matches!(c.status, RuntimeControlEvaluationStatus::Fail)
    });
    if fail_lineage_dataset {
        if !reasons.iter().any(|r| r == "dataset_lineage_required") {
            reasons.push("dataset_lineage_required".into());
            reasons.sort();
        }
        return ("BLOCKED", reasons);
    }

    let has_fail = merged
        .iter()
        .any(|c| matches!(c.status, RuntimeControlEvaluationStatus::Fail));

    let has_blocked_mapping = merged.iter().any(|c| {
        c.control_id == "GOVAI.GOVERNANCE.REASON_MAPPING"
            && matches!(c.status, RuntimeControlEvaluationStatus::Fail)
            && c.reason_codes.iter().any(|x| x == "unknown_reason_code")
    });

    let has_blocked_context = merged.iter().any(|c| {
        c.control_id == "GOVAI.GOVERNANCE.CONTEXT"
            && matches!(c.status, RuntimeControlEvaluationStatus::Fail)
            && c.reason_codes
                .iter()
                .any(|x| x == "governance_context_incomplete")
    });

    if has_blocked_context || has_blocked_mapping {
        if !reasons.iter().any(|r| {
            r == "governance_context_incomplete"
                || r == "unknown_reason_code"
                || r == "dataset_lineage_required"
        }) && has_blocked_context
        {
            reasons.push("governance_context_incomplete".into());
        }
        if has_blocked_mapping && !reasons.iter().any(|r| r == "unknown_reason_code") {
            reasons.push("unknown_reason_code".into());
        }
        reasons.sort();
        return ("BLOCKED", reasons);
    }

    if has_fail {
        reasons.sort();
        return ("INVALID", reasons);
    }

    reasons.sort();
    ("VALID", reasons)
}

#[cfg(test)]
mod runtime_governance_enforcement_tests {
    use super::{
        collect_unmapped_runtime_reason_codes, summarize_merged_controls, unknown_reason_control,
        GovernanceEnforcementMode, RuntimeControlEvaluation, RuntimeControlEvaluationStatus,
    };

    #[test]
    fn parses_enforcement_missing_and_invalid_as_off() {
        std::env::remove_var("GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT");
        assert!(matches!(
            GovernanceEnforcementMode::from_env(),
            GovernanceEnforcementMode::Off
        ));
        std::env::set_var("GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT", "  ");
        assert!(matches!(
            GovernanceEnforcementMode::from_env(),
            GovernanceEnforcementMode::Off
        ));
        std::env::set_var("GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT", "bogus");
        assert!(matches!(
            GovernanceEnforcementMode::from_env(),
            GovernanceEnforcementMode::Off
        ));
        std::env::remove_var("GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT");
    }

    #[test]
    fn parses_shadow_and_enforced() {
        std::env::set_var("GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT", "shadow");
        assert!(matches!(
            GovernanceEnforcementMode::from_env(),
            GovernanceEnforcementMode::Shadow
        ));
        std::env::set_var("GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT", "ENFORCED");
        assert!(matches!(
            GovernanceEnforcementMode::from_env(),
            GovernanceEnforcementMode::Enforced
        ));
        std::env::remove_var("GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT");
    }

    #[test]
    fn unmapped_reason_adds_blocked_unknown_summary_when_enforced() {
        let unmapped = RuntimeControlEvaluation {
            control_id: "ACME.UNKNOWN".into(),
            status: RuntimeControlEvaluationStatus::Warn,
            source: "fixture".into(),
            reason_codes: vec!["acme_placeholder_reason_xyz".into()],
        };
        let mut gov = vec![unmapped];
        assert!(collect_unmapped_runtime_reason_codes(&gov));
        gov.push(unknown_reason_control(GovernanceEnforcementMode::Enforced, true).unwrap());
        let (verdict, rs) = summarize_merged_controls(&gov);
        assert_eq!(verdict, "BLOCKED");
        assert!(rs.iter().any(|r| r == "unknown_reason_code"));
    }
}

#[cfg(test)]
mod capability_shadow_advisory_tests {
    use super::capability_shadow_advisory_evaluations;

    #[test]
    fn capability_declared_emits_pass() {
        let ev = capability_shadow_advisory_evaluations(true, Some("cap.v1"), false, None);
        assert_eq!(ev.len(), 1);
        let j = serde_json::to_value(&ev).unwrap();
        assert_eq!(j[0]["control_id"], "GOVAI.AGENT.CAPABILITY_DECLARED");
        assert_eq!(j[0]["status"], "PASS");
        assert_eq!(j[0]["source"], "capability_shadow");
        assert_eq!(j[0]["reason_codes"], serde_json::json!([]));
    }

    #[test]
    fn delegation_mismatch_emits_warn() {
        let ev =
            capability_shadow_advisory_evaluations(true, Some("cap.agent"), true, Some("cap.edge"));
        assert_eq!(ev.len(), 2);
        let j = serde_json::to_value(&ev).unwrap();
        assert_eq!(j[0]["control_id"], "GOVAI.AGENT.CAPABILITY_DECLARED");
        assert_eq!(
            j[1]["control_id"],
            "GOVAI.AGENT.CAPABILITY_DELEGATION_MISMATCH"
        );
        assert_eq!(j[1]["status"], "WARN");
        assert_eq!(
            j[1]["reason_codes"],
            serde_json::json!(["capability_delegation_mismatch"])
        );
    }

    #[test]
    fn delegation_without_capabilities_emits_undeclared_warn() {
        let ev = capability_shadow_advisory_evaluations(true, None, true, None);
        assert_eq!(ev.len(), 1);
        let j = serde_json::to_value(&ev).unwrap();
        assert_eq!(j[0]["control_id"], "GOVAI.AGENT.CAPABILITY_UNDECLARED");
        assert_eq!(
            j[0]["reason_codes"],
            serde_json::json!(["capability_undeclared"])
        );
    }
}

fn is_nonempty_opt(s: &Option<String>) -> bool {
    s.as_ref().is_some_and(|v| !v.trim().is_empty())
}

fn is_hex_64(s: &str) -> bool {
    if s.len() != 64 {
        return false;
    }
    s.chars()
        .all(|c| matches!(c, '0'..='9' | 'a'..='f' | 'A'..='F'))
}

/// Normalizes validated SHA-256 digest tokens (64 hex digits or `sha256:<64 hex>`) to lowercase hex form.
fn normalize_sha256_digest_token(raw: &str) -> Option<String> {
    let t = raw.trim();
    if t.is_empty() {
        return None;
    }
    if let Some(rest) = t.strip_prefix("sha256:") {
        if is_hex_64(rest) {
            return Some(format!("sha256:{}", rest.to_ascii_lowercase()));
        }
        return None;
    }
    if is_hex_64(t) {
        return Some(t.to_ascii_lowercase());
    }
    None
}

fn validate_sha256_digest_format(raw: &str) -> bool {
    normalize_sha256_digest_token(raw).is_some()
}

async fn runtime_evaluate_route(
    State(audit): State<AuditState>,
    headers: HeaderMap,
    Json(req): Json<RuntimeEvaluateRequest>,
) -> (StatusCode, Json<serde_json::Value>) {
    let (log_path, ledger_tid) = match tenant_log_path(&audit, &headers) {
        Ok(p) => p,
        Err(e) => {
            return api_err(
                StatusCode::BAD_REQUEST,
                "MISSING_TENANT_CONTEXT",
                "Missing tenant context.",
                "Provide `Authorization: Bearer <api_key>`.",
                Some(serde_json::Value::String(e)),
                Some(audit.policy_version),
                None,
            );
        }
    };

    let correlation_id = req
        .correlation_id
        .as_deref()
        .unwrap_or("")
        .trim()
        .to_string();
    if correlation_id.is_empty() {
        return api_err(
            StatusCode::BAD_REQUEST,
            "VALIDATION_ERROR",
            "Missing correlation_id.",
            "Provide a non-empty correlation_id to link this decision to a runtime request.",
            None,
            Some(audit.policy_version),
            None,
        );
    }
    let action = req.action.as_deref().unwrap_or("").trim().to_string();
    if action.is_empty() {
        return api_err(
            StatusCode::BAD_REQUEST,
            "VALIDATION_ERROR",
            "Missing action.",
            "Provide a non-empty action describing the runtime operation to be governed.",
            None,
            Some(audit.policy_version),
            None,
        );
    }
    if !(is_nonempty_opt(&req.artifact_digest)
        || is_nonempty_opt(&req.model_digest)
        || is_nonempty_opt(&req.deployment_digest))
    {
        return api_err(
            StatusCode::BAD_REQUEST,
            "VALIDATION_ERROR",
            "Missing artifact/model/deployment digest.",
            "Provide at least one digest: artifact_digest, model_digest, or deployment_digest.",
            None,
            Some(audit.policy_version),
            None,
        );
    }

    // Format validation only (no attestation): accept `sha256:<64hex>` or `<64hex>`.
    for (field, v) in [
        ("artifact_digest", &req.artifact_digest),
        ("model_digest", &req.model_digest),
        ("deployment_digest", &req.deployment_digest),
    ] {
        if let Some(s) = v.as_deref() {
            let t = s.trim();
            if !t.is_empty() && !validate_sha256_digest_format(t) {
                return api_err(
                    StatusCode::BAD_REQUEST,
                    "VALIDATION_ERROR",
                    &format!("Invalid {field}."),
                    "Provide a SHA-256 digest as 64 hex characters or `sha256:<64 hex>`.",
                    Some(json!({ "field": field })),
                    Some(audit.policy_version),
                    None,
                );
            }
        }
    }

    let lineage_input = req.dataset_lineage_refs.unwrap_or_default();
    let mut dataset_lineage_refs: Vec<RuntimeDatasetLineageRef> =
        Vec::with_capacity(lineage_input.len());
    for (idx, r) in lineage_input.into_iter().enumerate() {
        let id = r.dataset_id.as_deref().unwrap_or("").trim();
        if id.is_empty() {
            return api_err(
                StatusCode::BAD_REQUEST,
                "VALIDATION_ERROR",
                "Invalid dataset_lineage_refs entry.",
                "Each entry requires a non-empty dataset_id.",
                Some(json!({ "field": "dataset_lineage_refs", "index": idx })),
                Some(audit.policy_version),
                None,
            );
        }
        let digest_src = match r.dataset_digest.as_deref() {
            Some(s) if !s.trim().is_empty() => s,
            _ => {
                return api_err(
                    StatusCode::BAD_REQUEST,
                    "VALIDATION_ERROR",
                    "Invalid dataset_digest.",
                    "Each dataset lineage ref requires a valid dataset_digest (64 hex or `sha256:<64 hex>`).",
                    Some(json!({ "field": "dataset_lineage_refs", "index": idx })),
                    Some(audit.policy_version),
                    None,
                );
            }
        };
        let Some(normalized_digest) = normalize_sha256_digest_token(digest_src) else {
            return api_err(
                StatusCode::BAD_REQUEST,
                "VALIDATION_ERROR",
                "Invalid dataset_digest.",
                "Provide a SHA-256 digest as 64 hex characters or `sha256:<64 hex>`.",
                Some(json!({ "field": "dataset_lineage_refs", "index": idx })),
                Some(audit.policy_version),
                None,
            );
        };
        dataset_lineage_refs.push(RuntimeDatasetLineageRef {
            dataset_id: id.to_string(),
            dataset_digest: normalized_digest,
        });
    }
    let dataset_lineage_refs_v =
        serde_json::to_value(&dataset_lineage_refs).expect("serialize dataset_lineage_refs");

    let decision_id = Uuid::new_v4().to_string();
    let runtime_run_id = format!("runtime_{correlation_id}");

    let (_override_ref_out, override_ref_v): (Option<RuntimeOverrideRef>, Value) = match req
        .override_ref
        .as_ref()
    {
        None => (None, Value::Null),
        Some(input) => {
            let oid = input.override_id.as_deref().unwrap_or("").trim();
            let tid = input.target_decision_id.as_deref().unwrap_or("").trim();
            if oid.is_empty() {
                return api_err(
                    StatusCode::BAD_REQUEST,
                    "VALIDATION_ERROR",
                    "Invalid override_ref.",
                    "override_id must be non-empty.",
                    Some(json!({ "field": "override_ref", "subfield": "override_id" })),
                    Some(audit.policy_version),
                    None,
                );
            }
            if tid.is_empty() {
                return api_err(
                    StatusCode::BAD_REQUEST,
                    "VALIDATION_ERROR",
                    "Invalid override_ref.",
                    "target_decision_id must be non-empty.",
                    Some(json!({ "field": "override_ref", "subfield": "target_decision_id" })),
                    Some(audit.policy_version),
                    None,
                );
            }
            if tid != decision_id && tid != runtime_run_id {
                return api_err(
                    StatusCode::BAD_REQUEST,
                    "VALIDATION_ERROR",
                    "Invalid override_ref.",
                    "target_decision_id must match this response decision_id or the correlation-derived runtime run id (runtime_<correlation_id>).",
                    Some(json!({ "field": "override_ref", "subfield": "target_decision_id" })),
                    Some(audit.policy_version),
                    None,
                );
            }
            let normalized = RuntimeOverrideRef {
                override_id: oid.to_string(),
                target_decision_id: tid.to_string(),
            };
            let v = serde_json::to_value(&normalized).expect("serialize override_ref");
            (Some(normalized), v)
        }
    };

    let mut parsed_agent_capability: Option<String> = None;
    let mut parsed_delegated_capability: Option<String> = None;
    let mut delegation_context_present = false;

    let agent_context_v: Value = match req.agent_context.as_ref() {
        None => Value::Null,
        Some(inp) => {
            let mut out = RuntimeAgentContext::default();
            if let Some(s) = &inp.agent_id {
                let t = s.trim();
                if t.is_empty() {
                    return api_err(
                        StatusCode::BAD_REQUEST,
                        "VALIDATION_ERROR",
                        "Invalid agent_context.",
                        "agent_id must be non-empty when provided.",
                        Some(json!({ "field": "agent_context", "subfield": "agent_id" })),
                        Some(audit.policy_version),
                        None,
                    );
                }
                out.agent_id = Some(t.to_string());
            }
            if let Some(s) = &inp.principal_id {
                let t = s.trim();
                if t.is_empty() {
                    return api_err(
                        StatusCode::BAD_REQUEST,
                        "VALIDATION_ERROR",
                        "Invalid agent_context.",
                        "principal_id must be non-empty when provided.",
                        Some(json!({ "field": "agent_context", "subfield": "principal_id" })),
                        Some(audit.policy_version),
                        None,
                    );
                }
                out.principal_id = Some(t.to_string());
            }
            if let Some(s) = &inp.delegation_id {
                let t = s.trim();
                if t.is_empty() {
                    return api_err(
                        StatusCode::BAD_REQUEST,
                        "VALIDATION_ERROR",
                        "Invalid agent_context.",
                        "delegation_id must be non-empty when provided.",
                        Some(json!({ "field": "agent_context", "subfield": "delegation_id" })),
                        Some(audit.policy_version),
                        None,
                    );
                }
                out.delegation_id = Some(t.to_string());
            }
            if let Some(s) = &inp.capability_id {
                let t = s.trim();
                if t.is_empty() {
                    return api_err(
                        StatusCode::BAD_REQUEST,
                        "VALIDATION_ERROR",
                        "Invalid agent_context.",
                        "capability_id must be non-empty when provided.",
                        Some(json!({ "field": "agent_context", "subfield": "capability_id" })),
                        Some(audit.policy_version),
                        None,
                    );
                }
                out.capability_id = Some(t.to_string());
            }

            parsed_agent_capability = out.capability_id.clone();

            let v = serde_json::to_value(&out).expect("serialize agent_context");
            match &v {
                Value::Object(m) if m.is_empty() => Value::Null,
                _ => v,
            }
        }
    };

    let delegation_context_v: Value = match req.delegation_context.as_ref() {
        None => Value::Null,
        Some(inp) => {
            delegation_context_present = true;
            let did = inp.delegation_id.as_deref().unwrap_or("").trim();
            if did.is_empty() {
                return api_err(
                    StatusCode::BAD_REQUEST,
                    "VALIDATION_ERROR",
                    "Invalid delegation_context.",
                    "delegation_id must be non-empty when delegation_context is present.",
                    Some(json!({ "field": "delegation_context", "subfield": "delegation_id" })),
                    Some(audit.policy_version),
                    None,
                );
            }
            let mut out = RuntimeDelegationContext {
                delegation_id: did.to_string(),
                parent_delegation_id: None,
                delegator_agent_id: None,
                delegatee_agent_id: None,
                delegated_capability_id: None,
                delegation_scope: None,
                expires_at: None,
            };
            if let Some(s) = &inp.parent_delegation_id {
                let t = s.trim();
                if t.is_empty() {
                    return api_err(
                        StatusCode::BAD_REQUEST,
                        "VALIDATION_ERROR",
                        "Invalid delegation_context.",
                        "parent_delegation_id must be non-empty when provided.",
                        Some(
                            json!({ "field": "delegation_context", "subfield": "parent_delegation_id" }),
                        ),
                        Some(audit.policy_version),
                        None,
                    );
                }
                out.parent_delegation_id = Some(t.to_string());
            }
            if let Some(s) = &inp.delegator_agent_id {
                let t = s.trim();
                if t.is_empty() {
                    return api_err(
                        StatusCode::BAD_REQUEST,
                        "VALIDATION_ERROR",
                        "Invalid delegation_context.",
                        "delegator_agent_id must be non-empty when provided.",
                        Some(
                            json!({ "field": "delegation_context", "subfield": "delegator_agent_id" }),
                        ),
                        Some(audit.policy_version),
                        None,
                    );
                }
                out.delegator_agent_id = Some(t.to_string());
            }
            if let Some(s) = &inp.delegatee_agent_id {
                let t = s.trim();
                if t.is_empty() {
                    return api_err(
                        StatusCode::BAD_REQUEST,
                        "VALIDATION_ERROR",
                        "Invalid delegation_context.",
                        "delegatee_agent_id must be non-empty when provided.",
                        Some(
                            json!({ "field": "delegation_context", "subfield": "delegatee_agent_id" }),
                        ),
                        Some(audit.policy_version),
                        None,
                    );
                }
                out.delegatee_agent_id = Some(t.to_string());
            }
            if let Some(s) = &inp.delegated_capability_id {
                let t = s.trim();
                if t.is_empty() {
                    return api_err(
                        StatusCode::BAD_REQUEST,
                        "VALIDATION_ERROR",
                        "Invalid delegation_context.",
                        "delegated_capability_id must be non-empty when provided.",
                        Some(
                            json!({ "field": "delegation_context", "subfield": "delegated_capability_id" }),
                        ),
                        Some(audit.policy_version),
                        None,
                    );
                }
                out.delegated_capability_id = Some(t.to_string());
            }
            if let Some(s) = &inp.delegation_scope {
                let t = s.trim();
                if t.is_empty() {
                    return api_err(
                        StatusCode::BAD_REQUEST,
                        "VALIDATION_ERROR",
                        "Invalid delegation_context.",
                        "delegation_scope must be non-empty when provided.",
                        Some(
                            json!({ "field": "delegation_context", "subfield": "delegation_scope" }),
                        ),
                        Some(audit.policy_version),
                        None,
                    );
                }
                out.delegation_scope = Some(t.to_string());
            }
            if let Some(s) = &inp.expires_at {
                let t = s.trim();
                if t.is_empty() {
                    return api_err(
                        StatusCode::BAD_REQUEST,
                        "VALIDATION_ERROR",
                        "Invalid delegation_context.",
                        "expires_at must be non-empty when provided.",
                        Some(json!({ "field": "delegation_context", "subfield": "expires_at" })),
                        Some(audit.policy_version),
                        None,
                    );
                }
                out.expires_at = Some(t.to_string());
            }
            parsed_delegated_capability = out.delegated_capability_id.clone();
            serde_json::to_value(&out).expect("serialize delegation_context")
        }
    };

    let capability_advisory = capability_shadow_advisory_evaluations(
        true,
        parsed_agent_capability.as_deref(),
        delegation_context_present,
        parsed_delegated_capability.as_deref(),
    );
    let capability_advisory_v =
        serde_json::to_value(&capability_advisory).expect("serialize advisory_control_evaluations");

    let mode = RuntimeEvaluateMode::from_env(audit.deployment_env);
    let (mode_str, base_verdict, base_reason_codes) = match mode {
        RuntimeEvaluateMode::Disabled => (
            "disabled".to_string(),
            "BLOCKED".to_string(),
            vec!["runtime_not_enabled".into()],
        ),
        RuntimeEvaluateMode::Shadow => (
            "shadow".to_string(),
            "VALID".to_string(),
            vec!["shadow_mode_no_enforcement".into()],
        ),
    };

    let ts_utc = Utc::now().to_rfc3339_opts(SecondsFormat::Secs, true);

    // Never store raw bearer token: only fingerprint.
    let actor = audit_api_key::raw_bearer_token(&headers)
        .map(key_fingerprint)
        .unwrap_or_else(|| "anonymous".to_string());

    let policy_bundle_version = {
        let v = audit
            .policy_store
            .resolve_for_request(&ledger_tid)
            .version()
            .trim()
            .to_string();
        if v.is_empty() {
            audit.policy_version.to_string()
        } else {
            v
        }
    };

    let risk = RuntimeRiskClass::parse_opt(req.risk_class);
    let gov_global = GovernanceEnforcementMode::from_env();
    let tenant_allow_hs = governance_enforcement_tenant_allowlist_from_env();
    let tenant_allowlisted = tenant_allow_hs.contains(&ledger_tid);
    let enforced_hard = gov_global == GovernanceEnforcementMode::Enforced && tenant_allowlisted;
    let response_enforcement_mode = match gov_global {
        GovernanceEnforcementMode::Off => "off",
        GovernanceEnforcementMode::Shadow => "shadow",
        GovernanceEnforcementMode::Enforced if tenant_allowlisted => "enforced",
        GovernanceEnforcementMode::Enforced => "shadow",
    };

    let control_evaluations = runtime_stub_control_evaluations(mode);
    let control_evaluations_v =
        serde_json::to_value(&control_evaluations).expect("serialize runtime control_evaluations");

    let primary_digest_present = runtime_primary_artifact_digest_for_governance(
        &req.artifact_digest,
        &req.model_digest,
        &req.deployment_digest,
    )
    .map(|raw| normalize_sha256_digest_token(raw.trim()).is_some())
    .unwrap_or(false);

    let gov_context_denylisted =
        enforced_hard && (!primary_digest_present || policy_bundle_version.trim().is_empty());

    let mut gov_merged = merge_runtime_governance_controls(
        &control_evaluations,
        gov_global,
        risk,
        dataset_lineage_refs.is_empty(),
        enforced_hard,
    );

    if gov_context_denylisted {
        gov_merged.push(RuntimeControlEvaluation {
            control_id: "GOVAI.GOVERNANCE.CONTEXT".into(),
            status: RuntimeControlEvaluationStatus::Fail,
            source: "governance_gate".into(),
            reason_codes: vec!["governance_context_incomplete".into()],
        });
    }

    if collect_unmapped_runtime_reason_codes(&gov_merged) {
        if let Some(c) = unknown_reason_control(gov_global, enforced_hard) {
            gov_merged.push(c);
        }
    }

    let (gov_summary_verdict, gov_summary_reasons) = summarize_merged_controls(&gov_merged);

    let runtime_pins_blocked = matches!(mode, RuntimeEvaluateMode::Disabled);
    let mut verdict = base_verdict.clone();
    let mut reason_codes = base_reason_codes.clone();
    if enforced_hard && !runtime_pins_blocked {
        match gov_summary_verdict {
            "BLOCKED" => {
                verdict = "BLOCKED".into();
                reason_codes.clone_from(&gov_summary_reasons);
            }
            "INVALID" => {
                verdict = "INVALID".into();
                reason_codes.clone_from(&gov_summary_reasons);
            }
            _ => {}
        }
    }

    let gov_merged_v = serde_json::to_value(&gov_merged)
        .expect("serialize governance_summary control evaluations");
    let governance_summary_json = json!({
        "verdict": gov_summary_verdict,
        "reason_codes": gov_summary_reasons,
        "control_evaluations": gov_merged_v,
        "advisory_control_evaluations": capability_advisory_v.clone(),
        "dataset_lineage_refs": dataset_lineage_refs_v.clone(),
        "override_ref": override_ref_v.clone(),
        "agent_context": agent_context_v.clone(),
        "delegation_context": delegation_context_v.clone(),
        "risk_class": runtime_risk_class_as_str(risk),
        "enforcement_mode": gov_global.as_str(),
        "enforced": enforced_hard,
    });

    let payload = json!({
        "schema_version": "aigov.runtime_decision.v0_preview",
        "preview": true,
        "tenant_id": ledger_tid,
        "correlation_id": correlation_id,
        "runtime_run_id": runtime_run_id,
        "decision_id": decision_id,
        "action": action,
        "artifact_digest": req.artifact_digest.as_ref().map(|s| s.trim()).filter(|s| !s.is_empty()),
        "model_digest": req.model_digest.as_ref().map(|s| s.trim()).filter(|s| !s.is_empty()),
        "deployment_digest": req.deployment_digest.as_ref().map(|s| s.trim()).filter(|s| !s.is_empty()),
        "trace_id": req.trace_id.as_ref().map(|s| s.trim()).filter(|s| !s.is_empty()),
        "request_fingerprint": req.request_fingerprint.as_ref().map(|s| s.trim()).filter(|s| !s.is_empty()),
        "verdict": verdict,
        "reason_codes": reason_codes,
        "mode": mode_str,

        // Additive runtime governance metadata (M7.1 shell + M7.2 control_evaluations mapping).
        "governance_enrichment": {
            "schema_version": "runtime.evaluate.response.v1",
            "governance_context_version": "runtime.governance.context.v1",
            "control_evaluations": control_evaluations_v.clone(),
            "dataset_lineage_refs": dataset_lineage_refs_v.clone(),
            "override_ref": override_ref_v.clone(),
            "agent_context": agent_context_v.clone(),
            "delegation_context": delegation_context_v.clone(),
            "ai_act_requirement_refs": [],
            "policy_bundle_version": policy_bundle_version,
            "enforcement": response_enforcement_mode,
            "governance_summary": governance_summary_json.clone(),
        }
    });

    let ev = EvidenceEvent {
        event_id: Uuid::new_v4().to_string(),
        event_type: "runtime_decision".to_string(),
        ts_utc,
        actor,
        system: "runtime".to_string(),
        run_id: payload["runtime_run_id"]
            .as_str()
            .unwrap_or("_")
            .to_string(),
        environment: Some(audit.deployment_env.as_str().to_string()),
        payload,
    };

    if let Err(e) = crate::audit_store::append_record(&log_path, ev) {
        return api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "APPEND_FAILED",
            "Could not append runtime decision event.",
            "Retry in a moment. If this persists, contact support.",
            Some(json!({ "raw": e })),
            Some(audit.policy_version),
            None,
        );
    }

    let http_body = json!({
        "schema_version": "runtime.evaluate.response.v1",
        "governance_context_version": "runtime.governance.context.v1",
        "preview": true,
        "mode": mode_str,
        "verdict": verdict,
        "reason_codes": reason_codes,
        "correlation_id": correlation_id,
        "decision_id": decision_id,
        "control_evaluations": control_evaluations_v,
        "dataset_lineage_refs": dataset_lineage_refs_v,
        "override_ref": override_ref_v,
        "agent_context": agent_context_v.clone(),
        "delegation_context": delegation_context_v.clone(),
        "ai_act_requirement_refs": [],
        "policy_bundle_version": policy_bundle_version,
        "enforcement": response_enforcement_mode,
        "governance_summary": governance_summary_json,
    });

    (StatusCode::OK, Json(http_body))
}

#[derive(Deserialize)]
struct ComplianceSummaryQuery {
    run_id: String,
}

async fn compliance_summary_route(
    State(audit): State<AuditState>,
    headers: HeaderMap,
    Query(q): Query<ComplianceSummaryQuery>,
) -> (StatusCode, Json<serde_json::Value>) {
    let run_id = match crate::ai_decision_audit::normalize_run_id(&q.run_id) {
        Ok(r) => r,
        Err(e) => {
            return api_err(
                StatusCode::BAD_REQUEST,
                "INVALID_RUN_ID",
                &e,
                "Provide a non-empty run_id under 256 characters.",
                None,
                Some(audit.policy_version),
                Some(json!({
                    "schema_version": "aigov.compliance_summary.v2",
                    "run_id": q.run_id,
                })),
            )
        }
    };
    let (log_path, _) = match tenant_log_path(&audit, &headers) {
        Ok(p) => p,
        Err(e) => {
            return api_err(
                StatusCode::BAD_REQUEST,
                "MISSING_TENANT_CONTEXT",
                "Missing tenant context.",
                "Provide `Authorization: Bearer <api_key>`.",
                Some(serde_json::Value::String(e)),
                Some(audit.policy_version),
                Some(json!({
                    "schema_version": "aigov.compliance_summary.v2",
                    "run_id": run_id,
                })),
            )
        }
    };
    match bundle::collect_events_for_run(&log_path, &run_id) {
        Ok(events) => {
            if events.is_empty() {
                return api_err(
                    StatusCode::NOT_FOUND,
                    "RUN_NOT_FOUND",
                    "No events were found for this run_id in the current tenant ledger.",
                    tenant_scoped_not_found_hint(),
                    None,
                    Some(audit.policy_version),
                    Some(json!({
                        "schema_version": "aigov.compliance_summary.v2",
                        "run_id": run_id,
                    })),
                );
            }
            let events = bundle::canonicalize_evidence_events(events);
            let deployment_environment = audit.deployment_env.as_str();
            let ledger_environment = events
                .last()
                .and_then(|e| e.environment.as_deref())
                .unwrap_or(deployment_environment);
            let ledger_environment_note = if ledger_environment == deployment_environment {
                serde_json::Value::Null
            } else {
                json!(format!(
                    "ledger environment ({ledger_environment}) does not match deployment ({deployment_environment})"
                ))
            };
            let artifact_path = bundle::find_model_artifact_path(&events);
            let lp = format!("rust/{}", log_path);
            let bundle_hash = bundle::bundle_sha256(
                &run_id,
                audit.policy_version,
                &lp,
                artifact_path.as_deref(),
                &events,
            );
            let derived = projection::derive_current_state_from_events_with_context(
                &run_id,
                &events,
                Some(bundle_hash),
                None,
            );
            let verdict = compliance_verdict_from_state(&derived);
            let requirements = json!({
                "required": derived.requirements.required,
                "satisfied": derived.requirements.satisfied,
                "missing": derived.requirements.missing,
                "required_requirements": derived.requirements.required_requirements,
                "satisfied_requirements": derived.requirements.satisfied_requirements,
                "missing_requirements": derived.requirements.missing_requirements
            });
            let blocked_reasons = blocked_reasons_from_state(&derived);

            if audit.metering.enabled {
                let key_hash = match audit_api_key::raw_bearer_token(&headers) {
                    None => {
                        return api_err(
                            StatusCode::UNAUTHORIZED,
                            "MISSING_API_KEY",
                            "Missing API key.",
                            "Provide `Authorization: Bearer <api_key>`.",
                            None,
                            None,
                            None,
                        );
                    }
                    Some(t) => key_fingerprint(t),
                };
                let team_id = match metering::team_id_for_key_hash(&audit.pool, &key_hash).await {
                    Ok(t) => t,
                    Err(e) => {
                        return api_err(
                            StatusCode::INTERNAL_SERVER_ERROR,
                            "METERING_ERROR",
                            "We could not load metering information for this API key.",
                            "Retry in a moment. If this persists, contact support (this is a server-side issue).",
                            Some(json!({ "raw": e.to_string() })),
                            Some(audit.policy_version),
                            None,
                        );
                    }
                };
                if let Some(team_id) = team_id {
                    let ym = metering::year_month_utc_now();
                    let _ = metering::increment_team_op_counter(
                        &audit.pool,
                        team_id,
                        ym,
                        metering::TeamOpCounter::ComplianceCheck,
                    )
                    .await;
                }
            } else {
                let tenant_id = project::billing_tenant_id(&headers);
                let _ =
                    evidence_usage::increment_compliance_check_usage(&audit.pool, &tenant_id).await;
            }

            let ledger_tid = project::require_tenant_id_for_ledger(&headers, audit.deployment_env)
                .unwrap_or_else(|_| "default".to_string());
            let _ = stripe_billing::record_usage_attribution(
                &audit.pool,
                &ledger_tid,
                stripe_billing::BILLING_UNIT_COMPLIANCE_CHECK,
                &run_id,
                Some(verdict),
            )
            .await;

            match verdict {
                "VALID" => {
                    let _ = crate::product_ops::try_record_first_milestone(
                        &audit.pool,
                        &ledger_tid,
                        "first_valid_verdict",
                        Some(run_id.as_str()),
                        json!({}),
                    )
                    .await;
                }
                "INVALID" => {
                    let _ = crate::product_ops::try_record_first_milestone(
                        &audit.pool,
                        &ledger_tid,
                        "first_invalid_verdict",
                        Some(run_id.as_str()),
                        json!({}),
                    )
                    .await;
                }
                "BLOCKED" => {
                    let _ = crate::product_ops::try_record_first_milestone(
                        &audit.pool,
                        &ledger_tid,
                        "first_blocked_verdict",
                        Some(run_id.as_str()),
                        json!({}),
                    )
                    .await;
                }
                _ => {}
            }
            let _ = crate::product_ops::recompute_tenant_health(&audit.pool, &ledger_tid).await;

            crate::runtime_metrics::inc_compliance_summary();
            crate::ops_log::compliance_summary_generated("ledger_bound", run_id.len(), verdict);

            (
                StatusCode::OK,
                Json(json!({
                    "ok": true,
                    "schema_version": "aigov.compliance_summary.v2",
                    "policy_version": audit.policy_version,
                    "deployment_environment": deployment_environment,
                    "ledger_environment": ledger_environment,
                    "ledger_environment_note": ledger_environment_note,
                    "run_id": run_id,
                    "verdict": verdict,
                    "requirements": requirements,
                    "blocked_reasons": blocked_reasons,
                    "current_state": derived,
                })),
            )
        }
        Err(e) => api_err(
            StatusCode::NOT_FOUND,
            "RUN_NOT_FOUND",
            "No events were found for this run_id in the current tenant ledger.",
            tenant_scoped_not_found_hint(),
            Some(json!({ "raw": e })),
            Some(audit.policy_version),
            Some(json!({
                "schema_version": "aigov.compliance_summary.v2",
                "run_id": run_id,
            })),
        ),
    }
}

fn compliance_verdict_from_state(state: &projection::ComplianceCurrentState) -> &'static str {
    // Authoritative rule order (server-side): evaluation → approval → promotion.
    // - INVALID: evaluation explicitly failed.
    // - VALID: evaluation passed, risk reviewed + human approved (approve), and promotion executed.
    // - BLOCKED: anything else (missing prerequisites / missing required evidence / not yet promoted).
    if state.model.evaluation_passed == Some(false) {
        return "INVALID";
    }

    // Discovery-driven evidence gates (and mandatory discovery completion): additive enforcement.
    if !state.requirements.missing.is_empty() {
        return "BLOCKED";
    }

    let eval_ok = state.model.evaluation_passed == Some(true);
    let risk_ok = state.approval.risk_review_decision.as_deref() == Some("approve");
    let approval_ok = state.approval.human_approval_decision.as_deref() == Some("approve");
    let promoted =
        state.model.promotion.model_promoted_present && state.model.promotion.state == "promoted";

    if eval_ok && risk_ok && approval_ok && promoted {
        "VALID"
    } else {
        "BLOCKED"
    }
}

#[derive(Debug, Serialize)]
struct BlockedReason {
    code: String,
    message: String,
}

fn blocked_reasons_from_state(state: &projection::ComplianceCurrentState) -> Vec<BlockedReason> {
    let missing: std::collections::BTreeSet<&str> = state
        .requirements
        .missing
        .iter()
        .map(|s| s.as_str())
        .collect();

    // Stable order and stable messages (contract).
    let mut out: Vec<BlockedReason> = Vec::new();
    let ordered: [(&str, &str); 5] = [
        (
            "ai_discovery_completed",
            "AI discovery scan must be completed before compliance decision.",
        ),
        (
            "model_registered",
            "Detected OpenAI usage requires model registration.",
        ),
        (
            "usage_policy_defined",
            "Detected OpenAI usage requires usage policy definition.",
        ),
        (
            "evaluation_completed",
            "Detected AI system requires evaluation evidence.",
        ),
        (
            "model_artifact_documented",
            "Detected model artifact requires documentation.",
        ),
    ];

    for (code, message) in ordered {
        if missing.contains(code) {
            out.push(BlockedReason {
                code: code.to_string(),
                message: message.to_string(),
            });
        }
    }

    // Additive: lifecycle / promotion gates.
    //
    // `compliance_verdict_from_state` can return BLOCKED even when discovery-driven evidence is
    // complete (missing is empty). In that case we must surface why the run is blocked.
    //
    // Stable order contract:
    // evaluation → risk review → human approval → promotion execution.
    if compliance_verdict_from_state(state) == "BLOCKED" && missing.is_empty() {
        if state.model.evaluation_passed.is_none() {
            out.push(BlockedReason {
                code: "evaluation_required".to_string(),
                message: "Evaluation must be reported (passed=true) before promotion readiness."
                    .to_string(),
            });
        }

        if state.approval.risk_review_decision.as_deref() != Some("approve") {
            out.push(BlockedReason {
                code: "awaiting_risk_review".to_string(),
                message: "Risk assessment review must be approved before promotion readiness."
                    .to_string(),
            });
        }

        if state.approval.human_approval_decision.as_deref() != Some("approve") {
            out.push(BlockedReason {
                code: "approval_required".to_string(),
                message: "Human approval is required before promotion readiness.".to_string(),
            });
        }

        if !(state.model.promotion.model_promoted_present
            && state.model.promotion.state == "promoted")
        {
            let code = match state.model.promotion.state.as_str() {
                "awaiting_risk_review" => "awaiting_risk_review",
                "awaiting_human_approval" => "approval_required",
                "awaiting_evaluation_passed" => "evaluation_required",
                "awaiting_promotion_execution" => "awaiting_promotion_execution",
                _ => "promotion_not_ready",
            };
            let message = match state.model.promotion.state.as_str() {
                "awaiting_promotion_execution" => {
                    "Promotion evidence (model_promoted) has not been recorded yet.".to_string()
                }
                "promoted" => "Promotion has been executed.".to_string(),
                other => format!("Promotion is not complete: state={other}."),
            };
            // Avoid duplicating the same code when earlier gates already emitted it.
            if !out.iter().any(|r| r.code == code) {
                out.push(BlockedReason {
                    code: code.to_string(),
                    message,
                });
            }
        }
    }
    out
}

#[cfg(test)]
mod discovery_enforcement_tests {
    use super::*;
    use crate::schema::EvidenceEvent;
    use serde_json::json;

    fn ev(
        run_id: &str,
        event_type: &str,
        event_id: &str,
        payload: serde_json::Value,
    ) -> EvidenceEvent {
        EvidenceEvent {
            event_id: event_id.to_string(),
            event_type: event_type.to_string(),
            ts_utc: "2026-04-21T12:00:00Z".to_string(),
            actor: "test".to_string(),
            system: "unit".to_string(),
            run_id: run_id.to_string(),
            environment: Some("dev".to_string()),
            payload,
        }
    }

    fn base_valid_bundle(run_id: &str) -> Vec<EvidenceEvent> {
        vec![
            ev(
                run_id,
                "evaluation_reported",
                "e1",
                json!({
                    "ai_system_id": "ai1",
                    "dataset_id": "d1",
                    "model_version_id": "m1",
                    "metric": "acc",
                    "value": 0.9,
                    "threshold": 0.8,
                    "passed": true,
                }),
            ),
            ev(
                run_id,
                "risk_reviewed",
                "r1",
                json!({
                    "ai_system_id": "ai1",
                    "dataset_id": "d1",
                    "model_version_id": "m1",
                    "risk_id": "risk-1",
                    "assessment_id": "assess-1",
                    "dataset_governance_commitment": "commit-1",
                    "decision": "approve",
                    "reviewer": "compliance",
                    "justification": "ok",
                }),
            ),
            ev(
                run_id,
                "human_approved",
                "h1",
                json!({
                    "scope": "model_promoted",
                    "decision": "approve",
                    "approver": "compliance_officer",
                    "justification": "ok",
                    "assessment_id": "assess-1",
                    "risk_id": "risk-1",
                    "dataset_governance_commitment": "commit-1",
                    "ai_system_id": "ai1",
                    "dataset_id": "d1",
                    "model_version_id": "m1",
                }),
            ),
            ev(
                run_id,
                "model_promoted",
                "p1",
                json!({
                    "artifact_path": "s3://bucket/model",
                    "promotion_reason": "ok",
                    "assessment_id": "assess-1",
                    "risk_id": "risk-1",
                    "dataset_governance_commitment": "commit-1",
                    "approved_human_event_id": "h1",
                    "ai_system_id": "ai1",
                    "dataset_id": "d1",
                    "model_version_id": "m1",
                }),
            ),
        ]
    }

    #[test]
    fn discovery_only_run_never_returns_blocked_without_reasons() {
        let run_id = "run_discovery_only";
        let events = vec![ev(
            run_id,
            "ai_discovery_reported",
            "d1",
            json!({ "openai": false, "transformers": false, "model_artifacts": false }),
        )];

        let state =
            projection::derive_current_state_from_events_with_context(run_id, &events, None, None);
        assert!(state.requirements.missing.is_empty());

        let verdict = compliance_verdict_from_state(&state);
        let reasons = blocked_reasons_from_state(&state);

        assert!(
            verdict == "VALID" || !reasons.is_empty(),
            "discovery-only run must be VALID or BLOCKED with explicit reasons"
        );
        assert!(
            !(verdict == "BLOCKED" && state.requirements.missing.is_empty() && reasons.is_empty()),
            "invariant: never BLOCKED with empty missing and empty blocked_reasons"
        );
    }

    #[test]
    fn no_ai_discovery_reported_blocks_with_missing_ai_discovery_completed() {
        let run_id = "run_no_discovery_event";
        let events = base_valid_bundle(run_id);
        let state =
            projection::derive_current_state_from_events_with_context(run_id, &events, None, None);
        assert_eq!(
            state.requirements.required,
            vec!["ai_discovery_completed".to_string()]
        );
        assert_eq!(state.requirements.satisfied, Vec::<String>::new());
        assert_eq!(
            state.requirements.missing,
            vec!["ai_discovery_completed".to_string()]
        );
        assert_eq!(compliance_verdict_from_state(&state), "BLOCKED");
        let reasons = blocked_reasons_from_state(&state);
        assert_eq!(reasons.len(), 1);
        assert_eq!(reasons[0].code, "ai_discovery_completed");
    }

    #[test]
    fn ai_discovery_reported_with_no_findings_adds_no_extra_requirements() {
        let run_id = "run_discovery_no_findings";
        let mut events = base_valid_bundle(run_id);
        events.push(ev(
            run_id,
            "ai_discovery_reported",
            "d1",
            json!({ "openai": false, "transformers": false, "model_artifacts": false }),
        ));
        let state =
            projection::derive_current_state_from_events_with_context(run_id, &events, None, None);
        assert_eq!(
            state.requirements.required,
            vec!["ai_discovery_completed".to_string()]
        );
        assert_eq!(
            state.requirements.satisfied,
            vec!["ai_discovery_completed".to_string()]
        );
        assert!(state.requirements.missing.is_empty());
        assert_eq!(compliance_verdict_from_state(&state), "VALID");
        assert!(blocked_reasons_from_state(&state).is_empty());
    }

    #[test]
    fn openai_discovery_without_evidence_blocks() {
        let run_id = "run_openai_blocked";
        let mut events = base_valid_bundle(run_id);
        events.push(ev(
            run_id,
            "ai_discovery_reported",
            "d1",
            json!({ "openai": true, "transformers": false, "model_artifacts": false }),
        ));
        let state =
            projection::derive_current_state_from_events_with_context(run_id, &events, None, None);
        assert!(state
            .requirements
            .required
            .contains(&"ai_discovery_completed".to_string()));
        assert!(state
            .requirements
            .satisfied
            .contains(&"ai_discovery_completed".to_string()));
        assert!(state
            .requirements
            .missing
            .contains(&"model_registered".to_string()));
        assert!(state
            .requirements
            .missing
            .contains(&"usage_policy_defined".to_string()));
        assert_eq!(compliance_verdict_from_state(&state), "BLOCKED");
        let reasons = blocked_reasons_from_state(&state);
        let codes: Vec<String> = reasons.into_iter().map(|r| r.code).collect();
        assert_eq!(
            codes,
            vec![
                "model_registered".to_string(),
                "usage_policy_defined".to_string()
            ]
        );
    }

    #[test]
    fn openai_discovery_with_required_evidence_can_pass() {
        let run_id = "run_openai_ok";
        let mut events = base_valid_bundle(run_id);
        events.push(ev(
            run_id,
            "ai_discovery_reported",
            "d1",
            json!({ "openai": true, "transformers": false, "model_artifacts": false }),
        ));
        events.push(ev(
            run_id,
            "model_registered",
            "mr1",
            json!({ "ref": "registry://model" }),
        ));
        events.push(ev(
            run_id,
            "usage_policy_defined",
            "up1",
            json!({ "policy_id": "pol-1" }),
        ));
        let state =
            projection::derive_current_state_from_events_with_context(run_id, &events, None, None);
        assert!(state.requirements.missing.is_empty());
        assert_eq!(compliance_verdict_from_state(&state), "VALID");
        assert!(blocked_reasons_from_state(&state).is_empty());
    }

    #[test]
    fn model_artifact_discovery_without_documentation_blocks() {
        let run_id = "run_artifact_blocked";
        let mut events = base_valid_bundle(run_id);
        events.push(ev(
            run_id,
            "ai_discovery_reported",
            "d1",
            json!({ "openai": false, "transformers": false, "model_artifacts": true }),
        ));
        let state =
            projection::derive_current_state_from_events_with_context(run_id, &events, None, None);
        assert!(state
            .requirements
            .required
            .contains(&"model_artifact_documented".to_string()));
        assert!(state
            .requirements
            .required
            .contains(&"evaluation_completed".to_string()));
        assert!(state
            .requirements
            .satisfied
            .contains(&"evaluation_completed".to_string()));
        assert_eq!(
            state.requirements.missing,
            vec!["model_artifact_documented".to_string()]
        );
        assert_eq!(compliance_verdict_from_state(&state), "BLOCKED");
        let reasons = blocked_reasons_from_state(&state);
        assert_eq!(reasons.len(), 1);
        assert_eq!(reasons[0].code, "model_artifact_documented");
    }

    #[test]
    fn later_failed_evaluation_overrides_pass_and_invalidates() {
        let run_id = "run_eval_fail_overrides";
        let mut events = base_valid_bundle(run_id);
        events.push(ev(
            run_id,
            "ai_discovery_reported",
            "d1",
            json!({ "openai": false, "transformers": false, "model_artifacts": false }),
        ));
        // Last `evaluation_reported` wins for `evaluation_passed`.
        events.push(ev(
            run_id,
            "evaluation_reported",
            "e2",
            json!({
                "ai_system_id": "ai1",
                "dataset_id": "d1",
                "model_version_id": "m1",
                "metric": "acc",
                "value": 0.1,
                "threshold": 0.8,
                "passed": false,
            }),
        ));
        let state =
            projection::derive_current_state_from_events_with_context(run_id, &events, None, None);
        assert!(state.requirements.missing.is_empty());
        assert_eq!(state.model.evaluation_passed, Some(false));
        assert_eq!(compliance_verdict_from_state(&state), "INVALID");
        assert!(blocked_reasons_from_state(&state).is_empty());
    }

    #[test]
    fn single_explicit_failed_evaluation_is_invalid() {
        let run_id = "run_eval_fail_only";
        let events = vec![
            ev(
                run_id,
                "ai_discovery_reported",
                "d0",
                json!({ "openai": false, "transformers": false, "model_artifacts": false }),
            ),
            ev(
                run_id,
                "evaluation_reported",
                "e1",
                json!({
                    "ai_system_id": "ai1",
                    "dataset_id": "d1",
                    "model_version_id": "m1",
                    "metric": "acc",
                    "value": 0.1,
                    "threshold": 0.8,
                    "passed": false,
                }),
            ),
        ];
        let state =
            projection::derive_current_state_from_events_with_context(run_id, &events, None, None);
        assert_eq!(state.model.evaluation_passed, Some(false));
        assert_eq!(compliance_verdict_from_state(&state), "INVALID");
    }
}

#[cfg(test)]
mod api_error_response_tests {
    use super::*;
    use axum::http::HeaderValue;
    use serde_json::Value;

    const TENANT_SCOPED_NOT_FOUND_HINT: &str =
        "The resource was not found under the current tenant context. Check the run_id and API key. Note: X-GovAI-Project does not determine the ledger tenant.";

    fn pool_lazy_for_tests() -> DbPool {
        sqlx::PgPool::connect_lazy("postgres://postgres:postgres@localhost/postgres")
            .expect("connect_lazy should not contact the database")
    }

    const COMPLIANCE_SUMMARY_TEST_API_KEY: &str = "compliance-summary-test-secret";
    const COMPLIANCE_SUMMARY_TEST_TENANT: &str = "team-alpha";

    fn compliance_summary_test_audit_state(ledger_base: &'static str) -> AuditState {
        AuditState {
            ledger_base,
            policy_version: "test_policy_v1",
            deployment_env: GovaiEnvironment::Dev,
            policy_store: {
                let resolved = crate::policy_config::load_for_deployment(GovaiEnvironment::Dev)
                    .expect("test policy load");
                crate::policy_store::PolicyStore::load_for_deployment(
                    GovaiEnvironment::Dev,
                    resolved,
                )
                .expect("policy store load")
            },
            pool: pool_lazy_for_tests(),
            metering: crate::metering::MeteringConfig {
                enabled: false,
                default_plan: crate::metering::GovaiPlan::Free,
            },
        }
    }

    fn compliance_summary_test_headers() -> HeaderMap {
        let _ = audit_api_key::register_runtime_api_key(
            COMPLIANCE_SUMMARY_TEST_API_KEY,
            COMPLIANCE_SUMMARY_TEST_TENANT,
        );
        let mut headers = HeaderMap::new();
        headers.insert(
            "authorization",
            HeaderValue::from_str(&format!("Bearer {COMPLIANCE_SUMMARY_TEST_API_KEY}"))
                .expect("static bearer header"),
        );
        headers
    }
fn empty_tenant_ledger_for_compliance_summary_tests(ledger_base: &str) {
    let tenant_ledger =
        project::resolve_ledger_path(ledger_base, COMPLIANCE_SUMMARY_TEST_TENANT);
    std::fs::write(&tenant_ledger, "").unwrap();
}
    #[tokio::test]
    async fn compliance_summary_run_not_found_is_404_with_standard_error_shape() {
        let tmp = tempfile::tempdir().unwrap();
        let ledger_base = tmp.path().join("audit_log.jsonl");
        let ledger_base_static: &'static str =
            Box::leak(ledger_base.to_str().unwrap().to_string().into_boxed_str());
        empty_tenant_ledger_for_compliance_summary_tests(ledger_base_static);

        let state = compliance_summary_test_audit_state(ledger_base_static);
        let headers = compliance_summary_test_headers();

        let missing_run_id = "a0000000-0000-4000-8000-000000000099";
        let (status, Json(body)) = compliance_summary_route(
            State(state),
            headers,
            Query(ComplianceSummaryQuery {
                run_id: missing_run_id.to_string(),
            }),
        )
        .await;

        assert_eq!(status, StatusCode::NOT_FOUND);
        assert_eq!(body.get("ok").and_then(Value::as_bool), Some(false));
        assert_eq!(
            body.pointer("/error/code").and_then(Value::as_str),
            Some("RUN_NOT_FOUND")
        );
        assert_eq!(
            body.pointer("/error/hint").and_then(Value::as_str),
            Some(TENANT_SCOPED_NOT_FOUND_HINT)
        );
    }

    #[tokio::test]
    async fn compliance_summary_malformed_run_id_is_400_with_standard_error_shape() {
        let tmp = tempfile::tempdir().unwrap();
        let ledger_base = tmp.path().join("audit_log.jsonl");
        let ledger_base_static: &'static str =
            Box::leak(ledger_base.to_str().unwrap().to_string().into_boxed_str());
        empty_tenant_ledger_for_compliance_summary_tests(ledger_base_static);

        let state = compliance_summary_test_audit_state(ledger_base_static);
        let headers = compliance_summary_test_headers();

        let (status, Json(body)) = compliance_summary_route(
            State(state),
            headers,
            Query(ComplianceSummaryQuery {
                run_id: "   ".to_string(),
            }),
        )
        .await;

        assert_eq!(status, StatusCode::BAD_REQUEST);
        assert_eq!(body.get("ok").and_then(Value::as_bool), Some(false));
        assert_eq!(
            body.pointer("/error/code").and_then(Value::as_str),
            Some("INVALID_RUN_ID")
        );
    }
}

#[derive(Clone)]
pub struct AppState {
    pub pool: DbPool,
}

#[derive(Deserialize)]
pub struct CreateAssessmentBody {
    pub system_name: String,
    pub intended_purpose: String,
    pub risk_class: String,
}

#[derive(Serialize)]
pub struct AssessmentOut {
    pub id: String,
    pub team_id: String,
    pub created_by: String,
    pub created_at: String,
    pub status: String,
    pub system_name: Option<String>,
    pub intended_purpose: Option<String>,
    pub risk_class: Option<String>,
}

#[derive(Serialize)]
pub struct TeamOut {
    pub id: String,
    pub name: String,
    /// Raw value from `team_members.role` (may be a legacy alias).
    pub role: String,
    /// Normalized enterprise role id (`admin`, `compliance_officer`, …).
    pub effective_role: String,
    pub permissions: rbac::ProductPermissions,
}

#[derive(Serialize)]
pub struct MeOut {
    pub user_id: String,
    pub teams: Vec<TeamOut>,
}

async fn me(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> (StatusCode, Json<serde_json::Value>) {
    let cfg = match AuthConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return api_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "CONFIG_ERROR",
                "Server authentication is not configured correctly.",
                "Contact support (this is a server-side configuration issue).",
                Some(json!({ "raw": e })),
                None,
                None,
            )
        }
    };

    let user = match crate::auth::require_user(&cfg, &headers).await {
        Ok(u) => u,
        Err(resp) => return resp,
    };

    let teams = match db::list_user_teams(&state.pool, &user.user_id).await {
        Ok(t) => t,
        Err(e) => return api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "DB_ERROR",
            "We could not load your teams.",
            "Retry in a moment. If this persists, contact support (this is a server-side issue).",
            Some(json!({ "raw": e.to_string() })),
            None,
            None,
        ),
    };

    let out = MeOut {
        user_id: user.user_id.to_string(),
        teams: teams
            .into_iter()
            .map(|t| {
                let nr = rbac::normalize_role(&t.role);
                TeamOut {
                    id: t.team_id.to_string(),
                    name: t.team_name,
                    effective_role: rbac::canonical_role_id(nr).to_string(),
                    permissions: rbac::permissions_for(nr),
                    role: t.role,
                }
            })
            .collect(),
    };

    let mut body = serde_json::to_value(&out).expect("serialize MeOut");
    if let serde_json::Value::Object(map) = &mut body {
        map.insert(
            "product_positioning".to_string(),
            crate::tenant_console_contract::product_positioning_v1(),
        );
    }

    (StatusCode::OK, Json(body))
}

pub(crate) async fn resolve_team_id(
    pool: &DbPool,
    user: &CurrentUser,
    headers: &HeaderMap,
) -> Result<Uuid, (StatusCode, Json<serde_json::Value>)> {
    let team_hdr = headers
        .get("x-govai-team-id")
        .and_then(|v| v.to_str().ok())
        .map(|s| s.trim().to_string());

    if let Some(team_str) = team_hdr {
        let team_id = match Uuid::parse_str(&team_str) {
            Ok(t) => t,
            Err(_) => {
                return Err((
                    StatusCode::BAD_REQUEST,
                    Json(json!({
                        "ok": false,
                        "error": "invalid_team_id",
                        "code": "invalid_team_id",
                        "message": "`x-govai-team-id` must be a valid UUID."
                    })),
                ))
            }
        };

        let ok = match db::is_team_member(pool, team_id, user.user_id).await {
            Ok(b) => b,
            Err(e) => {
                return Err((
                    StatusCode::INTERNAL_SERVER_ERROR,
                    Json(json!({
                        "ok": false,
                        "error": "db_error",
                        "code": "db_error",
                        "message": "We could not verify team membership. Please retry.",
                        "details": e.to_string()
                    })),
                ))
            }
        };

        if !ok {
            return Err((
                StatusCode::FORBIDDEN,
                Json(json!({
                    "ok": false,
                    "error": "not_team_member",
                    "code": "not_team_member",
                    "message": "You are not a member of the selected team."
                })),
            ));
        }

        return Ok(team_id);
    }

    match db::get_default_team_for_user(pool, user.user_id).await {
        Ok(Some(team_id)) => Ok(team_id),
        Ok(None) => match db::bootstrap_team_for_user(pool, user.user_id).await {
            Ok(team_id) => Ok(team_id),
            Err(e) => Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({
                    "ok": false,
                    "error": "db_error",
                    "code": "db_error",
                    "message": "We could not create a default team for this user.",
                    "details": e.to_string()
                })),
            )),
        },
        Err(e) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({
                "ok": false,
                "error": "db_error",
                "code": "db_error",
                "message": "We could not load your default team.",
                "details": e.to_string()
            })),
        )),
    }
}

pub(crate) async fn team_product_permissions(
    pool: &DbPool,
    team_id: Uuid,
    user_id: Uuid,
) -> Result<rbac::ProductPermissions, (StatusCode, Json<serde_json::Value>)> {
    let role_raw = match db::get_team_member_role(pool, team_id, user_id).await {
        Ok(Some(r)) => r,
        Ok(None) => {
            return Err((
                StatusCode::FORBIDDEN,
                Json(json!({
                    "ok": false,
                    "error": "not_team_member",
                    "code": "not_team_member",
                    "message": "You are not a member of the selected team."
                })),
            ))
        }
        Err(e) => {
            return Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({
                    "ok": false,
                    "error": "db_error",
                    "code": "db_error",
                    "message": "We could not load your permissions. Please retry.",
                    "details": e.to_string()
                })),
            ))
        }
    };
    Ok(rbac::permissions_for_db_role(&role_raw))
}

async fn create_assessment(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<CreateAssessmentBody>,
) -> (StatusCode, Json<serde_json::Value>) {
    let cfg = match AuthConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "config_error",
                "Server authentication is not configured correctly.",
                None,
                Some(json!({ "details": e })),
            )
        }
    };

    let user = match crate::auth::require_user(&cfg, &headers).await {
        Ok(u) => u,
        Err(resp) => return resp,
    };

    let team_id = match resolve_team_id(&state.pool, &user, &headers).await {
        Ok(t) => t,
        Err(resp) => return resp,
    };

    let perms = match team_product_permissions(&state.pool, team_id, user.user_id).await {
        Ok(p) => p,
        Err(resp) => return resp,
    };
    if !perms.decision_submit {
        return (
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "error": "forbidden",
                "code": "insufficient_role",
                "message": "You do not have permission to perform this action.",
                "reason": "INSUFFICIENT_ROLE",
                "required_permission": "decision_submit"
            })),
        );
    }

    let rec = match db::insert_assessment(
        &state.pool,
        team_id,
        user.user_id,
        body.system_name,
        body.intended_purpose,
        body.risk_class,
    )
    .await
    {
        Ok(r) => r,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "We could not create the assessment. Please retry.",
                None,
                Some(json!({ "details": e.to_string() })),
            )
        }
    };

    let out = AssessmentOut {
        id: rec.id.to_string(),
        team_id: rec.team_id.to_string(),
        created_by: rec.created_by.to_string(),
        created_at: rec.created_at.to_rfc3339(),
        status: rec.status,
        system_name: rec.system_name,
        intended_purpose: rec.intended_purpose,
        risk_class: rec.risk_class,
    };

    (StatusCode::OK, Json(json!(out)))
}

#[derive(Deserialize)]
struct TenantLedgerBindingBody {
    ledger_tenant_id: String,
}

async fn tenant_console_ai_decision_audit_snapshot(
    pool: &DbPool,
    ledger_scope: &str,
    ledger_tid: Option<&str>,
    perms: &rbac::ProductPermissions,
) -> Value {
    let relation = "Immutable ledger compliance verdict for a run is only authoritative from GET /compliance-summary. This block lists append-only AI operational telemetry (multi-agent flight recorder) from Postgres when ledger-bound and permitted; it does not replace ledger verdict semantics.";
    if ledger_tid.is_none() || ledger_scope == "unbound" {
        return json!({
            "ledger_scope": "unbound",
            "data_source": "ledger_binding_required",
            "relation_to_compliance_summary": relation,
            "recent_traces": [],
            "ai_decision_trace_read": perms.ai_decision_trace_read,
        });
    }
    let lt = ledger_tid.unwrap();
    if !perms.ai_decision_trace_read {
        return json!({
            "ledger_scope": "bound",
            "data_source": "forbidden",
            "ledger_tenant_id": lt,
            "relation_to_compliance_summary": relation,
            "recent_traces": [],
            "ai_decision_trace_read": false,
        });
    }
    match crate::ai_decision_audit::list_recent_run_summaries(pool, lt, 20).await {
        Ok(rows) => json!({
            "ledger_scope": "bound",
            "data_source": "postgres",
            "ledger_tenant_id": lt,
            "relation_to_compliance_summary": relation,
            "recent_traces": rows,
            "ai_decision_trace_read": true,
        }),
        Err(e) => json!({
            "ledger_scope": "bound",
            "data_source": "unavailable",
            "ledger_tenant_id": lt,
            "relation_to_compliance_summary": relation,
            "recent_traces": [],
            "error": e.to_string(),
            "ai_decision_trace_read": true,
        }),
    }
}

async fn tenant_console_snapshot(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> (StatusCode, Json<Value>) {
    use serde_json::Value as JsonValue;
    use std::collections::HashSet;

    let generated_at = Utc::now().to_rfc3339_opts(SecondsFormat::Millis, true);
    let deployment_env =
        crate::govai_environment::resolve_from_env().unwrap_or(GovaiEnvironment::Dev);

    let cfg = match AuthConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "config_error",
                "Server authentication is not configured correctly.",
                None,
                Some(json!({ "details": e })),
            )
        }
    };

    let user = match crate::auth::require_user(&cfg, &headers).await {
        Ok(u) => u,
        Err(resp) => return resp,
    };

    let team_id = match resolve_team_id(&state.pool, &user, &headers).await {
        Ok(t) => t,
        Err(resp) => return resp,
    };

    let perms = match team_product_permissions(&state.pool, team_id, user.user_id).await {
        Ok(p) => p,
        Err(resp) => return resp,
    };

    let rbac_json = serde_json::to_value(&perms).unwrap_or_else(|_| json!({}));

    if !perms.tenant_console_read {
        let _ = db::insert_identity_audit_log(
            &state.pool,
            team_id,
            user.user_id,
            "deny",
            "tenant_console",
            "snapshot",
            json!({ "reason": "insufficient_role" }),
        )
        .await;
        return (
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "error": "forbidden",
                "code": "insufficient_role",
                "message": "You do not have permission to perform this action.",
                "reason": "INSUFFICIENT_ROLE",
                "required_permission": "tenant_console_read"
            })),
        );
    }

    let identity_audit = match db::list_identity_audit_for_team(&state.pool, team_id, 24).await {
        Ok(v) => v,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "Could not read identity audit log.",
                None,
                Some(json!({ "details": e.to_string() })),
            )
        }
    };

    let ledger_opt =
        match crate::product_ops::get_ledger_tenant_for_team(&state.pool, team_id).await {
            Ok(x) => x,
            Err(e) => {
                return json_error(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "db_error",
                    "Could not read ledger binding.",
                    None,
                    Some(json!({ "details": e.to_string() })),
                )
            }
        };

    let Some(ledger_tid) = ledger_opt else {
        let ai_decision_audit =
            tenant_console_ai_decision_audit_snapshot(&state.pool, "unbound", None, &perms).await;
        crate::ops_log::tenant_console_snapshot_served("unbound", true);
        return (
            StatusCode::OK,
            Json(json!({
                "ok": true,
                "snapshot_version": tenant_console_contract::SNAPSHOT_SCHEMA_VERSION,
                "product_positioning": tenant_console_contract::product_positioning_v1(),
                "generated_at": generated_at,
                "tenant": {
                    "user_id": user.user_id.to_string(),
                    "team_id": team_id.to_string(),
                },
                "audit_backend": tenant_console_audit_backend_block(deployment_env),
                "runtime_enforcement": tenant_console_runtime_enforcement_block(),
                "ledger_binding": {
                    "configured": false,
                    "ledger_tenant_id": JsonValue::Null,
                    "hint": "POST /api/tenant-console/ledger-binding with ledger_tenant_id (admin) to link this team to a GovAI ledger tenant."
                },
                "readiness": {
                    "summary": "ledger_binding_required",
                    "health": JsonValue::Null,
                    "milestone_first_touch_codes": json!([]),
                },
                "rbac": rbac_json,
                "product_operations": {
                    "ledger_scope": "unbound",
                    "autonomy_ingest_enforcement_enabled": crate::autonomous_runtime::autonomy_enforcement_enabled_from_env(),
                    "autonomy_policy": JsonValue::Null,
                    "milestones_recent": json!([]),
                },
                "ai_decision_audit": ai_decision_audit,
                "recent_events": {
                    "governance_identity_audit": identity_audit,
                    "product_milestones": json!([]),
                },
            })),
        );
    };

    let events = match crate::product_ops::list_product_events_for_tenant(
        &state.pool,
        &ledger_tid,
        50,
    )
    .await
    {
        Ok(v) => v,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "Could not list product events.",
                None,
                Some(json!({ "details": e.to_string() })),
            )
        }
    };

    let _ = crate::product_ops::recompute_tenant_health(&state.pool, &ledger_tid).await;
    let health = match crate::product_ops::get_tenant_health_row(&state.pool, &ledger_tid).await {
        Ok(h) => h,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "Could not load tenant health.",
                None,
                Some(json!({ "details": e.to_string() })),
            )
        }
    };

    let aut = match crate::product_ops::load_autonomy_policy(&state.pool, &ledger_tid).await {
        Ok(x) => x,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "Could not load autonomy policy.",
                None,
                Some(json!({ "details": e.to_string() })),
            )
        }
    };

    let mut milestone_codes: Vec<String> = events
        .iter()
        .filter_map(|e| e.get("event_type").and_then(|v| v.as_str()))
        .filter(|t| t.starts_with("first_"))
        .map(|s| s.to_string())
        .collect::<HashSet<_>>()
        .into_iter()
        .collect();
    milestone_codes.sort();

    let health_summary = match &health {
        None => "unknown",
        Some(h) => {
            let score = h.get("health_score").and_then(|v| v.as_i64()).unwrap_or(0);
            if score < 40 {
                "attention"
            } else {
                "ok"
            }
        }
    };

    let autonomy_policy_json = aut.as_ref().map(|p| {
        json!({
            "ledger_tenant_id": p.ledger_tenant_id,
            "autonomy_level": p.autonomy_level,
            "allowed_capabilities": p.allowed_capabilities,
            "requires_dual_approval": p.requires_dual_approval,
            "requires_override_reference": p.requires_override_reference,
        })
    });

    let milestones_recent = Value::Array(events.clone());
    let product_milestones = Value::Array(events);

    let ai_decision_audit = tenant_console_ai_decision_audit_snapshot(
        &state.pool,
        "bound",
        Some(ledger_tid.as_str()),
        &perms,
    )
    .await;

    crate::ops_log::tenant_console_snapshot_served("bound", true);

    (
        StatusCode::OK,
        Json(json!({
            "ok": true,
            "snapshot_version": tenant_console_contract::SNAPSHOT_SCHEMA_VERSION,
            "product_positioning": tenant_console_contract::product_positioning_v1(),
            "generated_at": generated_at,
            "tenant": {
                "user_id": user.user_id.to_string(),
                "team_id": team_id.to_string(),
            },
            "audit_backend": tenant_console_audit_backend_block(deployment_env),
            "runtime_enforcement": tenant_console_runtime_enforcement_block(),
            "ledger_binding": {
                "configured": true,
                "ledger_tenant_id": ledger_tid,
                "hint": JsonValue::Null,
            },
            "readiness": {
                "summary": health_summary,
                "health": health.unwrap_or(JsonValue::Null),
                "milestone_first_touch_codes": milestone_codes,
            },
            "rbac": rbac_json,
            "product_operations": {
                "ledger_scope": "bound",
                "ledger_tenant_id": ledger_tid,
                "autonomy_ingest_enforcement_enabled": crate::autonomous_runtime::autonomy_enforcement_enabled_from_env(),
                "autonomy_policy": autonomy_policy_json,
                "milestones_recent": milestones_recent,
            },
            "ai_decision_audit": ai_decision_audit,
            "recent_events": {
                "governance_identity_audit": identity_audit,
                "product_milestones": product_milestones,
            },
        })),
    )
}

async fn tenant_console_crm_export(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> (StatusCode, Json<Value>) {
    let cfg = match AuthConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "config_error",
                "Server authentication is not configured correctly.",
                None,
                Some(json!({ "details": e })),
            )
        }
    };

    let user = match crate::auth::require_user(&cfg, &headers).await {
        Ok(u) => u,
        Err(resp) => return resp,
    };

    let team_id = match resolve_team_id(&state.pool, &user, &headers).await {
        Ok(t) => t,
        Err(resp) => return resp,
    };

    let perms = match team_product_permissions(&state.pool, team_id, user.user_id).await {
        Ok(p) => p,
        Err(resp) => return resp,
    };

    if !perms.customer_success_export {
        return (
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "code": "insufficient_role",
                "required_permission": "customer_success_export"
            })),
        );
    }

    let ledger_opt =
        match crate::product_ops::get_ledger_tenant_for_team(&state.pool, team_id).await {
            Ok(x) => x,
            Err(e) => {
                return json_error(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "db_error",
                    "Could not read ledger binding.",
                    None,
                    Some(json!({ "details": e.to_string() })),
                )
            }
        };

    let Some(ledger_tid) = ledger_opt else {
        return json_error(
            StatusCode::BAD_REQUEST,
            "ledger_binding_missing",
            "Link a ledger tenant via POST /api/tenant-console/ledger-binding first.",
            None,
            None,
        );
    };

    let events =
        match crate::product_ops::list_product_events_for_tenant(&state.pool, &ledger_tid, 500)
            .await
        {
            Ok(v) => v,
            Err(e) => {
                return json_error(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "db_error",
                    "Could not list product events.",
                    None,
                    Some(json!({ "details": e.to_string() })),
                )
            }
        };

    let health = crate::product_ops::get_tenant_health_row(&state.pool, &ledger_tid)
        .await
        .ok()
        .flatten();
    let ndjson = crate::product_ops::crm_export_jsonl(&events, health);
    (
        StatusCode::OK,
        Json(json!({
            "ok": true,
            "format": "ndjson",
            "ledger_tenant_id": ledger_tid,
            "ndjson": ndjson
        })),
    )
}

#[derive(Deserialize)]
struct OnboardingProvisionBody {
    #[serde(default)]
    confirm: bool,
}

async fn onboarding_provision(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<OnboardingProvisionBody>,
) -> (StatusCode, Json<Value>) {
let hosted_enabled = crate::audit_api_key::hosted_self_service_enabled();

if !hosted_enabled && std::env::var("GOVAI_TEST_MODE").is_err() {
    return (
        StatusCode::NOT_IMPLEMENTED,
        Json(json!({
            "ok": false,
            "code": "hosted_self_service_disabled",
            "message": "Hosted self-service provisioning is not enabled on this deployment."
        })),
    );
}

    if !body.confirm {
        return json_error(
            StatusCode::BAD_REQUEST,
            "confirm_required",
            "Set confirm=true to issue an API key.",
            None,
            None,
        );
    }

    let cfg = match AuthConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "config_error",
                "Server authentication is not configured correctly.",
                None,
                Some(json!({ "details": e })),
            )
        }
    };

    let user = match crate::auth::require_user(&cfg, &headers).await {
        Ok(u) => u,
        Err(resp) => return resp,
    };

    let team_id = match resolve_team_id(&state.pool, &user, &headers).await {
        Ok(t) => t,
        Err(resp) => return resp,
    };

    match crate::hosted_provisioning::provision_team(&state.pool, team_id, user.user_id).await {
        Ok(result) => (
            StatusCode::CREATED,
            Json(json!({
                "ok": true,
                "team_id": result.team_id.to_string(),
                "ledger_tenant_id": result.ledger_tenant_id,
                "api_key": result.api_key,
                "key_prefix": result.key_prefix,
                "message": "Store this API key now; it cannot be retrieved again."
            })),
        ),
        Err(e) if e.starts_with("api_key_already_issued:") => (
            StatusCode::CONFLICT,
            Json(json!({
                "ok": false,
                "code": "api_key_already_issued",
                "message": "This team already has an active API key. Rotate via operator support or revoke the existing key first."
            })),
        ),
        Err(e) => json_error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "provision_failed",
            "Could not provision hosted API key.",
            None,
            Some(json!({ "details": e })),
        ),
    }
}

async fn onboarding_status(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> (StatusCode, Json<Value>) {
    let cfg = match AuthConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "config_error",
                "Server authentication is not configured correctly.",
                None,
                Some(json!({ "details": e })),
            )
        }
    };

    let user = match crate::auth::require_user(&cfg, &headers).await {
        Ok(u) => u,
        Err(resp) => return resp,
    };

    let team_id = match resolve_team_id(&state.pool, &user, &headers).await {
        Ok(t) => t,
        Err(resp) => return resp,
    };

    match crate::hosted_provisioning::onboarding_status(&state.pool, team_id).await {
        Ok(status) => (
            StatusCode::OK,
            Json(json!({
                "ok": true,
                "hosted_self_service": crate::audit_api_key::hosted_self_service_enabled(),
                "onboarding": status
            })),
        ),
        Err(e) => json_error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "db_error",
            "Could not load onboarding status.",
            None,
            Some(json!({ "details": e.to_string() })),
        ),
    }
}

async fn tenant_console_ledger_binding(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<TenantLedgerBindingBody>,
) -> (StatusCode, Json<Value>) {
    let cfg = match AuthConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "config_error",
                "Server authentication is not configured correctly.",
                None,
                Some(json!({ "details": e })),
            )
        }
    };

    let user = match crate::auth::require_user(&cfg, &headers).await {
        Ok(u) => u,
        Err(resp) => return resp,
    };

    let team_id = match resolve_team_id(&state.pool, &user, &headers).await {
        Ok(t) => t,
        Err(resp) => return resp,
    };

    let perms = match team_product_permissions(&state.pool, team_id, user.user_id).await {
        Ok(p) => p,
        Err(resp) => return resp,
    };

    if !perms.admin_override {
        return (
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "code": "insufficient_role",
                "required_permission": "admin_override"
            })),
        );
    }

    let lt = body.ledger_tenant_id.trim().to_string();
    if lt.is_empty() {
        return json_error(
            StatusCode::BAD_REQUEST,
            "invalid_body",
            "ledger_tenant_id is required.",
            None,
            None,
        );
    }

    if let Err(e) = crate::product_ops::upsert_team_ledger_binding(&state.pool, team_id, &lt).await
    {
        return json_error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "db_error",
            "Could not save binding.",
            None,
            Some(json!({ "details": e.to_string() })),
        );
    }

    let _ = db::insert_identity_audit_log(
        &state.pool,
        team_id,
        user.user_id,
        "tenant_console",
        "ledger_binding",
        &lt,
        json!({}),
    )
    .await;

    (
        StatusCode::OK,
        Json(json!({
            "ok": true,
            "team_id": team_id.to_string(),
            "ledger_tenant_id": lt
        })),
    )
}

pub fn assessments_router(pool: DbPool) -> Router {
    assessments_core_router(pool.clone())
        .merge(crate::tenant_http::router(pool.clone()))
        .merge(crate::ai_decision_http::router(pool.clone()))
        .merge(crate::govai_functions_v2::router(pool))
}

fn assessments_core_router(pool: DbPool) -> Router {
    let state = AppState { pool };

    Router::new()
        .route("/api/me", get(me))
        .route("/api/assessments", post(create_assessment))
        .route("/api/tenant-console/snapshot", get(tenant_console_snapshot))
        .route(
            "/api/tenant-console/crm-export",
            get(tenant_console_crm_export),
        )
        .route(
            "/api/tenant-console/ledger-binding",
            post(tenant_console_ledger_binding),
        )
        .route("/api/onboarding/status", get(onboarding_status))
        .route("/api/onboarding/provision", post(onboarding_provision))
        .with_state(state)
}

#[derive(Serialize)]
pub struct ComplianceWorkflowOut {
    pub id: String,
    pub team_id: String,
    pub run_id: String,
    pub state: String,
    pub created_at: String,
    pub updated_at: String,
    pub created_by: String,
    pub updated_by: Option<String>,
}

fn workflow_to_out(r: db::ComplianceWorkflowRow) -> ComplianceWorkflowOut {
    ComplianceWorkflowOut {
        id: r.id.to_string(),
        team_id: r.team_id.to_string(),
        run_id: r.run_id,
        state: r.state,
        created_at: r.created_at.to_rfc3339(),
        updated_at: r.updated_at.to_rfc3339(),
        created_by: r.created_by.to_string(),
        updated_by: r.updated_by.map(|u| u.to_string()),
    }
}

/// Declares that authoritative promotion readiness comes only from the ledger projection (`GET /compliance-summary`).
/// `compliance_workflow` is an operational queue / org override layer, not a second source of compliance truth.
fn decision_authority_object() -> serde_json::Value {
    json!({
        "primary": "ledger_projection",
        "pipeline": ["immutable_ledger", "bundle", "projection", "compliance_summary"],
        "workflow_role": "operational_queue_override",
        "note": "compliance_workflow rows do not replace immutable evidence; reconcile with GET /compliance-summary."
    })
}

fn json_ok_workflow(workflow: ComplianceWorkflowOut) -> serde_json::Value {
    json!({
        "ok": true,
        "workflow": workflow,
        "decision_authority": decision_authority_object(),
    })
}

#[derive(Deserialize)]
pub struct ListWorkflowQuery {
    pub state: Option<String>,
}

#[derive(Deserialize)]
pub struct RegisterWorkflowBody {
    pub run_id: String,
}

#[derive(Deserialize)]
pub struct ReviewDecisionBody {
    /// `"approve"` or `"reject"`
    pub decision: String,
}

#[derive(Deserialize)]
pub struct PromotionDecisionBody {
    /// `"allow"` or `"block"`
    pub decision: String,
}

#[derive(Deserialize)]
pub struct DelegateApprovalBody {
    /// `"review"` or `"promotion"`
    pub scope: String,
    /// Supabase user id (UUID) receiving the delegation.
    pub delegatee_user_id: String,
}

async fn list_compliance_workflow(
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(q): Query<ListWorkflowQuery>,
) -> (StatusCode, Json<serde_json::Value>) {
    let cfg = match AuthConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "config_error",
                "Server authentication is not configured correctly.",
                None,
                Some(json!({ "details": e })),
            )
        }
    };

    let user = match crate::auth::require_user(&cfg, &headers).await {
        Ok(u) => u,
        Err(resp) => return resp,
    };

    let team_id = match resolve_team_id(&state.pool, &user, &headers).await {
        Ok(t) => t,
        Err(resp) => return resp,
    };

    let perms = match team_product_permissions(&state.pool, team_id, user.user_id).await {
        Ok(p) => p,
        Err(resp) => return resp,
    };
    if !perms.review_queue_view {
        return (
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "error": "forbidden",
                "code": "insufficient_role",
                "message": "You do not have permission to perform this action.",
                "reason": "INSUFFICIENT_ROLE",
                "required_permission": "review_queue_view"
            })),
        );
    }

    let filter = q.state.as_deref().filter(|s| !s.trim().is_empty());
    let rows = match db::list_compliance_workflow(&state.pool, team_id, filter).await {
        Ok(r) => r,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "We could not load workflow items. Please retry.",
                None,
                Some(json!({ "details": e.to_string() })),
            )
        }
    };

    let out: Vec<ComplianceWorkflowOut> = rows.into_iter().map(workflow_to_out).collect();
    (
        StatusCode::OK,
        Json(json!({
            "ok": true,
            "items": out,
            "decision_authority": decision_authority_object(),
        })),
    )
}

async fn register_compliance_workflow(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<RegisterWorkflowBody>,
) -> (StatusCode, Json<serde_json::Value>) {
    let cfg = match AuthConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "config_error",
                "Server authentication is not configured correctly.",
                None,
                Some(json!({ "details": e })),
            )
        }
    };

    let user = match crate::auth::require_user(&cfg, &headers).await {
        Ok(u) => u,
        Err(resp) => return resp,
    };

    let team_id = match resolve_team_id(&state.pool, &user, &headers).await {
        Ok(t) => t,
        Err(resp) => return resp,
    };

    let perms = match team_product_permissions(&state.pool, team_id, user.user_id).await {
        Ok(p) => p,
        Err(resp) => return resp,
    };
    if !perms.decision_submit {
        return (
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "error": "forbidden",
                "code": "insufficient_role",
                "message": "You do not have permission to perform this action.",
                "reason": "INSUFFICIENT_ROLE",
                "required_permission": "decision_submit"
            })),
        );
    }

    let run_id = body.run_id.trim().to_string();
    if run_id.is_empty() {
        return json_error(
            StatusCode::BAD_REQUEST,
            "run_id_required",
            "Missing required field `run_id`.",
            None,
            None,
        );
    }

    let rec = match db::upsert_workflow_pending(&state.pool, team_id, &run_id, user.user_id).await {
        Ok(r) => r,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "We could not register this run in the workflow. Please retry.",
                None,
                Some(json!({ "details": e.to_string() })),
            )
        }
    };

    (StatusCode::OK, Json(json_ok_workflow(workflow_to_out(rec))))
}

async fn get_compliance_workflow_one(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(run_id): Path<String>,
) -> (StatusCode, Json<serde_json::Value>) {
    let cfg = match AuthConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "config_error",
                "Server authentication is not configured correctly.",
                None,
                Some(json!({ "details": e })),
            )
        }
    };

    let user = match crate::auth::require_user(&cfg, &headers).await {
        Ok(u) => u,
        Err(resp) => return resp,
    };

    let team_id = match resolve_team_id(&state.pool, &user, &headers).await {
        Ok(t) => t,
        Err(resp) => return resp,
    };

    let perms = match team_product_permissions(&state.pool, team_id, user.user_id).await {
        Ok(p) => p,
        Err(resp) => return resp,
    };
    if !perms.review_queue_view {
        return (
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "error": "forbidden",
                "code": "insufficient_role",
                "message": "You do not have permission to perform this action.",
                "reason": "INSUFFICIENT_ROLE",
                "required_permission": "review_queue_view"
            })),
        );
    }

    let rid = run_id.trim();
    let rec = match db::get_compliance_workflow(&state.pool, team_id, rid).await {
        Ok(r) => r,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "We could not load this workflow item. Please retry.",
                None,
                Some(json!({ "details": e.to_string() })),
            )
        }
    };

    match rec {
        Some(r) => (StatusCode::OK, Json(json_ok_workflow(workflow_to_out(r)))),
        None => (
            StatusCode::NOT_FOUND,
            Json(json!({
                "ok": false,
                "error": "not_found",
                "code": "not_found",
                "message": "Workflow item not found for this run_id."
            })),
        ),
    }
}

async fn post_review_decision(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(run_id): Path<String>,
    Json(body): Json<ReviewDecisionBody>,
) -> (StatusCode, Json<serde_json::Value>) {
    let cfg = match AuthConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "config_error",
                "Server authentication is not configured correctly.",
                None,
                Some(json!({ "details": e })),
            )
        }
    };

    let user = match crate::auth::require_user(&cfg, &headers).await {
        Ok(u) => u,
        Err(resp) => return resp,
    };

    let team_id = match resolve_team_id(&state.pool, &user, &headers).await {
        Ok(t) => t,
        Err(resp) => return resp,
    };

    let perms = match team_product_permissions(&state.pool, team_id, user.user_id).await {
        Ok(p) => p,
        Err(resp) => return resp,
    };
    if !perms.decision_submit {
        return (
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "error": "forbidden",
                "code": "insufficient_role",
                "message": "You do not have permission to perform this action.",
                "reason": "INSUFFICIENT_ROLE",
                "required_permission": "decision_submit"
            })),
        );
    }

    let rid = run_id.trim().to_string();
    if rid.is_empty() {
        return json_error(
            StatusCode::BAD_REQUEST,
            "run_id_required",
            "Missing required path parameter run_id.",
            None,
            None,
        );
    }

    let approve = match body.decision.trim() {
        "approve" => true,
        "reject" => false,
        _ => {
            return json_error(
                StatusCode::BAD_REQUEST,
                "invalid_decision",
                "Invalid decision. Expected `approve` or `reject`.",
                None,
                Some(json!({ "expected": ["approve", "reject"] })),
            )
        }
    };

    // Separation of duties: workflow owner cannot review their own run unless explicitly delegated.
    if let Ok(Some(wf)) = db::get_compliance_workflow(&state.pool, team_id, &rid).await {
        if wf.created_by == user.user_id {
            let delegated =
                db::has_workflow_delegation(&state.pool, team_id, &rid, "review", user.user_id)
                    .await
                    .unwrap_or(false);
            if !delegated {
                return json_error(
                    StatusCode::FORBIDDEN,
                    "separation_of_duties",
                    "Separation-of-duties: workflow owner cannot review their own run.",
                    None,
                    None,
                );
            }
        }
    }

    let rec =
        match db::transition_workflow_review(&state.pool, team_id, &rid, user.user_id, approve)
            .await
        {
            Ok(r) => r,
            Err(e) => {
                return json_error(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "db_error",
                    "We could not persist the review decision. Please retry.",
                    None,
                    Some(json!({ "details": e.to_string() })),
                )
            }
        };

    let _ = db::insert_identity_audit_log(
        &state.pool,
        team_id,
        user.user_id,
        "workflow_review",
        "run",
        &rid,
        json!({ "decision": body.decision }),
    )
    .await;

    match rec {
        Some(r) => (StatusCode::OK, Json(json_ok_workflow(workflow_to_out(r)))),
        None => (
            StatusCode::CONFLICT,
            Json(json!({
                "ok": false,
                "error": "invalid_state",
                "code": "invalid_state",
                "message": "Invalid workflow state: expected pending_review for review decision."
            })),
        ),
    }
}

async fn post_promotion_decision(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(run_id): Path<String>,
    Json(body): Json<PromotionDecisionBody>,
) -> (StatusCode, Json<serde_json::Value>) {
    let cfg = match AuthConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "config_error",
                "Server authentication is not configured correctly.",
                None,
                Some(json!({ "details": e })),
            )
        }
    };

    let user = match crate::auth::require_user(&cfg, &headers).await {
        Ok(u) => u,
        Err(resp) => return resp,
    };

    let team_id = match resolve_team_id(&state.pool, &user, &headers).await {
        Ok(t) => t,
        Err(resp) => return resp,
    };

    let perms = match team_product_permissions(&state.pool, team_id, user.user_id).await {
        Ok(p) => p,
        Err(resp) => return resp,
    };
    if !perms.promotion_action {
        return (
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "error": "forbidden",
                "code": "insufficient_role",
                "message": "You do not have permission to perform this action.",
                "reason": "INSUFFICIENT_ROLE",
                "required_permission": "promotion_action"
            })),
        );
    }

    let rid = run_id.trim().to_string();
    if rid.is_empty() {
        return json_error(
            StatusCode::BAD_REQUEST,
            "run_id_required",
            "Missing required path parameter run_id.",
            None,
            None,
        );
    }

    let allow = match body.decision.trim() {
        "allow" => true,
        "block" => false,
        _ => {
            return json_error(
                StatusCode::BAD_REQUEST,
                "invalid_decision",
                "Invalid decision. Expected `allow` or `block`.",
                None,
                Some(json!({ "expected": ["allow", "block"] })),
            )
        }
    };

    // Separation of duties: workflow owner cannot decide promotion for their own run unless explicitly delegated.
    if let Ok(Some(wf)) = db::get_compliance_workflow(&state.pool, team_id, &rid).await {
        if wf.created_by == user.user_id {
            let delegated =
                db::has_workflow_delegation(&state.pool, team_id, &rid, "promotion", user.user_id)
                    .await
                    .unwrap_or(false);
            if !delegated {
                return json_error(
                    StatusCode::FORBIDDEN,
                    "separation_of_duties",
                    "Separation-of-duties: workflow owner cannot decide promotion for their own run.",
                    None,
                    None,
                );
            }
        }
    }

    let rec =
        match db::transition_workflow_promotion(&state.pool, team_id, &rid, user.user_id, allow)
            .await
        {
            Ok(r) => r,
            Err(e) => {
                return json_error(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "db_error",
                    "We could not persist the promotion decision. Please retry.",
                    None,
                    Some(json!({ "details": e.to_string() })),
                )
            }
        };

    let _ = db::insert_identity_audit_log(
        &state.pool,
        team_id,
        user.user_id,
        "workflow_promotion",
        "run",
        &rid,
        json!({ "decision": body.decision }),
    )
    .await;

    match rec {
        Some(r) => (
            StatusCode::OK,
            Json(json!({ "ok": true, "workflow": workflow_to_out(r) })),
        ),
        None => (
            StatusCode::CONFLICT,
            Json(json!({
                "ok": false,
                "error": "invalid_state",
                "code": "invalid_state",
                "message": "Invalid workflow state: expected approved for promotion decision."
            })),
        ),
    }
}

async fn post_delegate_approval(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(run_id): Path<String>,
    Json(body): Json<DelegateApprovalBody>,
) -> (StatusCode, Json<serde_json::Value>) {
    let cfg = match AuthConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return json_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "config_error",
                "Server authentication is not configured correctly.",
                None,
                Some(json!({ "details": e })),
            )
        }
    };

    let user = match crate::auth::require_user(&cfg, &headers).await {
        Ok(u) => u,
        Err(resp) => return resp,
    };

    let team_id = match resolve_team_id(&state.pool, &user, &headers).await {
        Ok(t) => t,
        Err(resp) => return resp,
    };

    let perms = match team_product_permissions(&state.pool, team_id, user.user_id).await {
        Ok(p) => p,
        Err(resp) => return resp,
    };
    if !perms.admin_override {
        return (
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "error": "forbidden",
                "code": "insufficient_role",
                "message": "You do not have permission to perform this action.",
                "reason": "INSUFFICIENT_ROLE",
                "required_permission": "admin_override"
            })),
        );
    }

    let rid = run_id.trim().to_string();
    if rid.is_empty() {
        return json_error(
            StatusCode::BAD_REQUEST,
            "run_id_required",
            "Missing required path parameter run_id.",
            None,
            None,
        );
    }

    let scope = body.scope.trim();
    if scope != "review" && scope != "promotion" {
        return json_error(
            StatusCode::BAD_REQUEST,
            "invalid_scope",
            "Invalid scope. Expected `review` or `promotion`.",
            None,
            Some(json!({ "expected": ["review", "promotion"] })),
        );
    }

    let delegatee = body.delegatee_user_id.trim();
    let delegatee = match Uuid::parse_str(delegatee) {
        Ok(u) => u,
        Err(_) => {
            return json_error(
                StatusCode::BAD_REQUEST,
                "invalid_delegatee_user_id",
                "Invalid delegatee_user_id (expected UUID).",
                None,
                None,
            )
        }
    };

    if let Err(e) =
        db::create_workflow_delegation(&state.pool, team_id, &rid, scope, user.user_id, delegatee)
            .await
    {
        return json_error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "db_error",
            "We could not persist the delegation. Please retry.",
            None,
            Some(json!({ "details": e.to_string() })),
        );
    }

    let _ = db::insert_identity_audit_log(
        &state.pool,
        team_id,
        user.user_id,
        "workflow_delegation_created",
        "run",
        &rid,
        json!({ "scope": scope, "delegatee_user_id": delegatee.to_string() }),
    )
    .await;

    (StatusCode::OK, Json(json!({ "ok": true })))
}

pub fn compliance_workflow_router(pool: DbPool) -> Router {
    let state = AppState { pool };

    Router::new()
        .route(
            "/api/compliance-workflow",
            get(list_compliance_workflow).post(register_compliance_workflow),
        )
        .route(
            "/api/compliance-workflow/:run_id",
            get(get_compliance_workflow_one),
        )
        .route(
            "/api/compliance-workflow/:run_id/review",
            post(post_review_decision),
        )
        .route(
            "/api/compliance-workflow/:run_id/promotion",
            post(post_promotion_decision),
        )
        .route(
            "/api/compliance-workflow/:run_id/delegate",
            post(post_delegate_approval),
        )
        .with_state(state)
}
