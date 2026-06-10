//! Core audit HTTP surface (ledger ingest, bundle, compliance summary, export).

use crate::api_error::{api_error, api_error_with};
use crate::api_usage::ApiUsageState;
use crate::audit_api_key::{
    gate_audit_routes_with_state, validate_api_key_allowlist_consistency, AuditApiKeyConfig,
    AuditKeyGateState, ResolvedLedgerTenant,
};
use crate::audit_export::build_audit_export_v1;
use crate::audit_store::{append_record_atomic_with_run_count, verify_chain};
use crate::bundle::{
    bundle_document_value, bundle_sha256, collect_events_for_run, find_model_artifact_path,
    portable_evidence_digest_v1,
};
use crate::compliance_summary::{
    compliance_summary_error_json, compliance_summary_success_json, derive_verdict_from_state,
};
use crate::db::{self, DbPool};
use crate::govai_environment::{self, GovaiEnvironment};
use crate::ledger_storage;
use crate::ledger_view::FileLedgerView;
use crate::metering;
use crate::ops_log;
use crate::policy_config::{self, PolicyConfig, PolicySource};
use crate::policy_store::PolicyStore;
use crate::projection::derive_current_state_from_events_with_context;
use crate::project;
use crate::runtime_diagnostics::{self, ProcessStartedAt};
use crate::runtime_metrics;
use crate::schema::EvidenceEvent;
use axum::extract::{Path, Query, State};
use axum::http::{HeaderMap, StatusCode};
use axum::middleware;
use axum::response::IntoResponse;
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::Deserialize;
use serde_json::{json, Value};
use sqlx::postgres::PgPoolOptions;
use std::sync::Arc;

const LEDGER_STEM: &str = "audit_log.jsonl";

#[derive(Clone)]
pub struct AppState {
    pub deployment_env: GovaiEnvironment,
    pub policy_store: Arc<PolicyStore>,
    pub legacy_policy: PolicyConfig,
    pub policy_source: PolicySource,
    pub pool: DbPool,
    pub usage: ApiUsageState,
    pub api_key_cfg: AuditApiKeyConfig,
    pub base_url: Option<String>,
    pub started_at: ProcessStartedAt,
}

#[derive(Debug, Deserialize)]
struct RunIdQuery {
    run_id: String,
}

async fn pool_from_env() -> Result<DbPool, String> {
    if db::postgres_url_configured_nonempty().is_err() {
        return PgPoolOptions::new()
            .max_connections(1)
            .connect_lazy("postgres://localhost:5432/govai_unused")
            .map_err(|e| format!("lazy pool: {e}"));
    }
    let pool = db::init_pool_from_env().await?;
    if matches!(
        std::env::var("GOVAI_AUTO_MIGRATE")
            .map(|s| s.trim().to_ascii_lowercase())
            .unwrap_or_default()
            .as_str(),
        "1" | "true" | "yes" | "on"
    ) {
        sqlx::migrate!("./migrations")
            .run(&pool)
            .await
            .map_err(|e| format!("migration failed: {e}"))?;
    }
    Ok(pool)
}

pub async fn build_app_state() -> Result<AppState, String> {
    let deployment_env = govai_environment::resolve_from_env()?;
    let resolved = policy_config::load_for_deployment(deployment_env)?;
    let policy_store = Arc::new(PolicyStore::load_for_deployment(
        deployment_env,
        resolved.clone(),
    )?);
    let _ = ledger_storage::validate_startup(deployment_env)?;
    crate::audit_api_key::init_api_key_tenant_map(deployment_env)?;
    validate_api_key_allowlist_consistency(deployment_env)?;
    let pool = pool_from_env().await?;
    let usage = ApiUsageState::from_env(&pool)?;
    let api_key_cfg = AuditApiKeyConfig::from_env();
    let base_url = std::env::var("GOVAI_BASE_URL")
        .or_else(|_| std::env::var("AIGOV_BASE_URL"))
        .ok()
        .filter(|s| !s.trim().is_empty());
    Ok(AppState {
        deployment_env,
        policy_store,
        legacy_policy: resolved.config,
        policy_source: resolved.source,
        pool,
        usage,
        api_key_cfg,
        base_url,
        started_at: ProcessStartedAt::now(),
    })
}

fn gate_state(st: &AppState) -> AuditKeyGateState {
    AuditKeyGateState {
        cfg: st.api_key_cfg.clone(),
        usage: st.usage.clone(),
        pool: st.pool.clone(),
        deployment_env: st.deployment_env,
    }
}

pub fn build_router(state: AppState) -> Router {
    let gate = gate_state(&state);
    let ledger_routes = Router::new()
        .route("/evidence", post(post_evidence))
        .route("/bundle", get(get_bundle_query))
        .route("/bundle/:run_id", get(get_bundle_path))
        .route("/bundle-hash", get(get_bundle_hash_query))
        .route("/bundle-hash/:run_id", get(get_bundle_hash_path))
        .route("/compliance-summary", get(get_compliance_summary_query))
        .route("/compliance-summary/:run_id", get(get_compliance_summary_path))
        .route("/api/export/:run_id", get(get_api_export))
        .route("/verify", get(get_verify))
        .route("/verify/:run_id", get(get_verify_run))
        .layer(middleware::from_fn_with_state(
            gate,
            gate_audit_routes_with_state,
        ));

    Router::new()
        .route("/", get(get_root))
        .route("/health", get(get_health))
        .route("/ready", get(get_ready))
        .route("/status", get(get_status))
        .merge(ledger_routes)
        .with_state(state)
}

async fn resolve_tenant(
    st: &AppState,
    headers: &HeaderMap,
    extensions: &axum::http::Extensions,
) -> Result<String, (StatusCode, Json<Value>)> {
    if let Some(ResolvedLedgerTenant(tid)) = extensions.get::<ResolvedLedgerTenant>() {
        return Ok(tid.clone());
    }
    project::require_tenant_id_for_ledger_async(&st.pool, headers, st.deployment_env)
        .await
        .map_err(|e| {
            api_error(
                StatusCode::BAD_REQUEST,
                "TENANT_RESOLUTION_FAILED",
                &e,
                "Configure GOVAI_API_KEYS_JSON mapping api_key -> ledger_tenant_id.",
                None,
            )
        })
}

fn ledger_path_for_tenant(tenant_id: &str) -> String {
    project::resolve_ledger_path(LEDGER_STEM, tenant_id)
}

fn active_policy_version(st: &AppState, tenant_id: &str) -> String {
    st.policy_store
        .resolve_for_request(tenant_id)
        .version()
        .to_string()
}

async fn get_root() -> Json<Value> {
    Json(json!({
        "ok": true,
        "service": "aigov_audit",
        "surface": "govai-core",
    }))
}

async fn get_health() -> Json<Value> {
    Json(json!({ "ok": true }))
}

async fn get_status(State(st): State<AppState>) -> Json<Value> {
    let body = runtime_diagnostics::build_status_body(&st, st.started_at, &st.policy_source).await;
    Json(body)
}

async fn get_ready(State(st): State<AppState>) -> impl IntoResponse {
    let checks = runtime_diagnostics::readiness_components(&st, true).await;
    let database_ping = checks
        .get("database_ping")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    let migrations_complete = checks
        .get("migrations_complete")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    let ledger_writable = checks
        .get("ledger_writable")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    let tenant_ledger_probe = checks
        .get("tenant_ledger_probe")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    let mut tenant_ledger_probe = false;
    if ledger_writable {
        let probe_path = project::resolve_ledger_path(LEDGER_STEM, "__ready_probe__");
        let probe = EvidenceEvent {
            event_id: format!("ready-probe-{}", uuid::Uuid::new_v4()),
            event_type: "ai_discovery_reported".to_string(),
            ts_utc: chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true),
            actor: "ready_probe".to_string(),
            system: "govai".to_string(),
            run_id: format!("ready-probe-{}", uuid::Uuid::new_v4()),
            environment: Some(st.deployment_env.as_str().to_string()),
            payload: json!({
                "openai": false,
                "transformers": false,
                "model_artifacts": false,
                "status": "probe",
            }),
            parent_run_id: None,
            root_run_id: None,
            delegated_from_event_id: None,
            agent_id: None,
            agent_role: None,
            delegation_reason: None,
        };
        tenant_ledger_probe = append_record_atomic_with_run_count(&probe_path, probe).is_ok();
    }

    let checks = json!({
        "database_ping": database_ping,
        "migrations_complete": migrations_complete,
        "ledger_writable": ledger_writable,
        "tenant_ledger_probe": tenant_ledger_probe,
    });

    let ready = database_ping && migrations_complete && ledger_writable && tenant_ledger_probe;
    if ready {
        return (
            StatusCode::OK,
            Json(json!({
                "ok": true,
                "ready": true,
                "checks": checks,
                "runtime_governance_enforcement": runtime_diagnostics::runtime_governance_enforcement_diag(),
            })),
        )
            .into_response();
    }

    api_error(
        StatusCode::SERVICE_UNAVAILABLE,
        "NOT_READY",
        "One or more readiness checks failed.",
        "Verify DATABASE_URL, apply migrations (GOVAI_AUTO_MIGRATE=true), and set GOVAI_LEDGER_DIR.",
        Some(json!({ "checks": checks })),
    )
    .into_response()
}

async fn post_evidence(
    State(st): State<AppState>,
    headers: HeaderMap,
    extensions: axum::http::Extensions,
    Json(mut event): Json<EvidenceEvent>,
) -> impl IntoResponse {
    let tenant_id = match resolve_tenant(&st, &headers, &extensions).await {
        Ok(t) => t,
        Err(e) => return e.into_response(),
    };
    let log_path = ledger_path_for_tenant(&tenant_id);
    let policy_version = active_policy_version(&st, &tenant_id);

    let existing = match collect_events_for_run(&log_path, &event.run_id) {
        Ok(e) => e,
        Err(e) => {
            return api_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "LEDGER_READ_ERROR",
                &e,
                "Retry later or contact the operator.",
                None,
            )
            .into_response();
        }
    };

    if let Err(e) =
        govai_environment::stamp_event_environment_for_ingest(&mut event, st.deployment_env, &existing)
    {
        return policy_violation_response(&policy_version, &e);
    }

    let ledger_view = FileLedgerView::new(&log_path);
    if let Err(v) = st.policy_store.enforce_ingest_for_request(&tenant_id, &event, &ledger_view) {
        return policy_violation_response(&policy_version, &v.to_string());
    }

    let append_result = append_record_atomic_with_run_count(&log_path, event.clone());
    match append_result {
        Ok((rec, pre_count)) => {
            runtime_metrics::inc_evidence_ingest("appended");
            ops_log::evidence_ingest("appended", 200, &tenant_id);
            let mut body = json!({
                "ok": true,
                "record_hash": rec.record_hash,
                "policy_version": policy_version,
                "environment": st.deployment_env.as_str(),
            });
            if metering::metering_enabled() {
                if let Some(extra) = metering::ingest_success_extras(
                    &tenant_id,
                    &event.run_id,
                    pre_count as u64,
                )
                .as_object()
                {
                    for (k, v) in extra {
                        body[k] = v.clone();
                    }
                }
            }
            (StatusCode::OK, Json(body)).into_response()
        }
        Err(e) if e.contains("duplicate event_id") => api_error(
            StatusCode::CONFLICT,
            "DUPLICATE_EVENT_ID",
            &e,
            "Use a new event_id or treat this ingest as idempotent no-op on the client.",
            Some(json!({ "policy_version": policy_version })),
        )
        .into_response(),
        Err(e) => api_error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "LEDGER_APPEND_ERROR",
            &e,
            "Retry the request; if the failure persists, check ledger storage.",
            None,
        )
        .into_response(),
    }
}

fn policy_violation_response(policy_version: &str, message: &str) -> axum::response::Response {
    let code = if message.contains("policy_violation:") {
        message
            .split(':')
            .nth(1)
            .map(|s| s.trim().split_whitespace().next().unwrap_or("policy_violation"))
            .unwrap_or("policy_violation")
    } else {
        "policy_violation"
    };
    api_error_with(
        StatusCode::BAD_REQUEST,
        "policy_violation",
        message,
        "Fix the event payload or ordering per policy documentation.",
        None,
        Some(json!({
            "code": code,
            "policy_version": policy_version,
            "metering": if metering::metering_enabled() { "on" } else { "off" },
        })),
    )
    .into_response()
}

async fn get_bundle_query(
    State(st): State<AppState>,
    headers: HeaderMap,
    extensions: axum::http::Extensions,
    Query(q): Query<RunIdQuery>,
) -> impl IntoResponse {
    bundle_for_run(&st, &headers, &extensions, &q.run_id).await
}

async fn get_bundle_path(
    State(st): State<AppState>,
    headers: HeaderMap,
    extensions: axum::http::Extensions,
    Path(run_id): Path<String>,
) -> impl IntoResponse {
    bundle_for_run(&st, &headers, &extensions, &run_id).await
}

async fn bundle_for_run(
    st: &AppState,
    headers: &HeaderMap,
    extensions: &axum::http::Extensions,
    run_id: &str,
) -> axum::response::Response {
    let tenant_id = match resolve_tenant(st, headers, extensions).await {
        Ok(t) => t,
        Err(e) => return e.into_response(),
    };
    let log_path = ledger_path_for_tenant(&tenant_id);
    let policy_version = active_policy_version(st, &tenant_id);

    let events = match collect_events_for_run(&log_path, run_id) {
        Ok(e) => e,
        Err(e) => {
            return Json(json!({
                "ok": false,
                "error": "ledger_read_error",
                "message": e,
                "policy_version": policy_version,
                "run_id": run_id,
            }))
            .into_response();
        }
    };

    if events.is_empty() {
        return Json(json!({
            "ok": false,
            "error": "run_not_found",
            "message": "No events for run_id in tenant ledger.",
            "policy_version": policy_version,
            "run_id": run_id,
        }))
        .into_response();
    }

    let doc = bundle_document_value(run_id, &policy_version, &log_path, &events);
    Json(doc).into_response()
}

async fn get_bundle_hash_query(
    State(st): State<AppState>,
    headers: HeaderMap,
    extensions: axum::http::Extensions,
    Query(q): Query<RunIdQuery>,
) -> impl IntoResponse {
    bundle_hash_for_run(&st, &headers, &extensions, &q.run_id).await
}

async fn get_bundle_hash_path(
    State(st): State<AppState>,
    headers: HeaderMap,
    extensions: axum::http::Extensions,
    Path(run_id): Path<String>,
) -> impl IntoResponse {
    bundle_hash_for_run(&st, &headers, &extensions, &run_id).await
}

async fn bundle_hash_for_run(
    st: &AppState,
    headers: &HeaderMap,
    extensions: &axum::http::Extensions,
    run_id: &str,
) -> axum::response::Response {
    let tenant_id = match resolve_tenant(st, headers, extensions).await {
        Ok(t) => t,
        Err(e) => return e.into_response(),
    };
    let log_path = ledger_path_for_tenant(&tenant_id);
    let policy_version = active_policy_version(st, &tenant_id);

    let events = match collect_events_for_run(&log_path, run_id) {
        Ok(e) => e,
        Err(e) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({
                    "ok": false,
                    "error": "ledger_read_error",
                    "message": e,
                })),
            )
                .into_response();
        }
    };

    if events.is_empty() {
        return (
            StatusCode::NOT_FOUND,
            Json(json!({
                "ok": false,
                "error": "run_not_found",
                "message": "No events for run_id in tenant ledger.",
                "policy_version": policy_version,
                "run_id": run_id,
            })),
        )
            .into_response();
    }

    let artifact = find_model_artifact_path(&events);
    let bundle_sha = bundle_sha256(
        run_id,
        &policy_version,
        &log_path,
        artifact.as_deref(),
        &events,
    );
    let events_content_sha256 = portable_evidence_digest_v1(run_id, &events);

    (
        StatusCode::OK,
        Json(json!({
            "ok": true,
            "run_id": run_id,
            "policy_version": policy_version,
            "bundle_sha256": bundle_sha,
            "events_content_sha256": events_content_sha256,
        })),
    )
        .into_response()
}

async fn get_compliance_summary_query(
    State(st): State<AppState>,
    headers: HeaderMap,
    extensions: axum::http::Extensions,
    Query(q): Query<RunIdQuery>,
) -> impl IntoResponse {
    compliance_summary_for_run(&st, &headers, &extensions, &q.run_id).await
}

async fn get_compliance_summary_path(
    State(st): State<AppState>,
    headers: HeaderMap,
    extensions: axum::http::Extensions,
    Path(run_id): Path<String>,
) -> impl IntoResponse {
    compliance_summary_for_run(&st, &headers, &extensions, &run_id).await
}

async fn compliance_summary_for_run(
    st: &AppState,
    headers: &HeaderMap,
    extensions: &axum::http::Extensions,
    run_id: &str,
) -> axum::response::Response {
    let tenant_id = match resolve_tenant(st, headers, extensions).await {
        Ok(t) => t,
        Err(e) => return e.into_response(),
    };
    let log_path = ledger_path_for_tenant(&tenant_id);
    let policy_version = active_policy_version(st, &tenant_id);

    let events = match collect_events_for_run(&log_path, run_id) {
        Ok(e) => e,
        Err(e) => {
            return Json(compliance_summary_error_json(
                run_id,
                &policy_version,
                "ledger_read_error",
                &e,
                None,
            ))
            .into_response();
        }
    };

    if events.is_empty() {
        return Json(compliance_summary_error_json(
            run_id,
            &policy_version,
            "run_not_found",
            "No events for run_id in tenant ledger.",
            None,
        ))
        .into_response();
    }

    let artifact = find_model_artifact_path(&events);
    let bundle_hash = bundle_sha256(
        run_id,
        &policy_version,
        &log_path,
        artifact.as_deref(),
        &events,
    );
    let exported_at = events.last().map(|e| e.ts_utc.clone());
    let state = derive_current_state_from_events_with_context(
        run_id,
        &events,
        Some(bundle_hash),
        exported_at,
    );
    let outcome = derive_verdict_from_state(&state, &st.legacy_policy);
    runtime_metrics::inc_compliance_summary();
    ops_log::compliance_summary_generated(&tenant_id, run_id.len(), &outcome.verdict);

    Json(compliance_summary_success_json(
        run_id,
        &policy_version,
        &state,
        &outcome,
    ))
    .into_response()
}

async fn get_api_export(
    State(st): State<AppState>,
    headers: HeaderMap,
    extensions: axum::http::Extensions,
    Path(run_id): Path<String>,
) -> impl IntoResponse {
    let tenant_id = match resolve_tenant(&st, &headers, &extensions).await {
        Ok(t) => t,
        Err(e) => return e.into_response(),
    };
    let log_path = ledger_path_for_tenant(&tenant_id);
    let policy_version = active_policy_version(&st, &tenant_id);

    match build_audit_export_v1(
        &run_id,
        &tenant_id,
        &log_path,
        &policy_version,
        st.deployment_env,
        &st.legacy_policy,
    ) {
        Ok(doc) => (StatusCode::OK, Json(doc)).into_response(),
        Err(e) if e == "run_not_found" => (
            StatusCode::NOT_FOUND,
            Json(json!({
                "ok": false,
                "error": "run_not_found",
                "message": "No events for run_id in tenant ledger.",
                "run_id": run_id,
            })),
        )
            .into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({
                "ok": false,
                "error": "export_failed",
                "message": e,
                "run_id": run_id,
            })),
        )
            .into_response(),
    }
}

async fn get_verify(
    State(st): State<AppState>,
    headers: HeaderMap,
    extensions: axum::http::Extensions,
) -> impl IntoResponse {
    verify_ledger(st, headers, extensions, None).await
}

async fn get_verify_run(
    State(st): State<AppState>,
    headers: HeaderMap,
    extensions: axum::http::Extensions,
    Path(run_id): Path<String>,
) -> impl IntoResponse {
    verify_ledger(st, headers, extensions, Some(run_id.as_str())).await
}

async fn verify_ledger(
    st: AppState,
    headers: HeaderMap,
    extensions: axum::http::Extensions,
    run_id_filter: Option<&str>,
) -> impl IntoResponse {
    let tenant_id = match resolve_tenant(&st, &headers, &extensions).await {
        Ok(t) => t,
        Err(e) => return e.into_response(),
    };
    let log_path = ledger_path_for_tenant(&tenant_id);

    match verify_chain(&log_path) {
        Ok(()) => {
            if let Some(rid) = run_id_filter {
                let events = collect_events_for_run(&log_path, rid).unwrap_or_default();
                if events.is_empty() {
                    return Json(json!({
                        "ok": false,
                        "error": "run_not_found",
                        "message": "No events for run_id in tenant ledger.",
                        "run_id": rid,
                    }))
                    .into_response();
                }
            }
            Json(json!({ "ok": true, "message": "chain valid" })).into_response()
        }
        Err(e) => Json(json!({
            "ok": false,
            "error": "chain_invalid",
            "message": e,
        }))
        .into_response(),
    }
}
