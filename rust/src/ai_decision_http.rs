//! HTTP API for append-only AI decision / multi-agent flight recorder traces (Postgres).
//!
//! Routes are merged into [`crate::govai_api::assessments_router`] and share [`crate::govai_api::AppState`].

use axum::extract::{Path, Query, State};
use axum::http::{HeaderMap, StatusCode};
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::Deserialize;
use serde_json::{json, Value};
use uuid::Uuid;

use crate::ai_decision_audit::{
    aggregate_trace_export, insert_trace_event, list_events_for_run_ordered,
    list_recent_run_summaries, normalize_run_id, preview_completed_verdict_detail,
    trace_has_started_event, validate_append_event, validate_trace_started_payload,
};
use crate::api_error::api_error_with;
use crate::auth::{AuthConfig, CurrentUser};
use crate::db::DbPool;
use crate::govai_api::{resolve_team_id, team_product_permissions, AppState};
use crate::rbac::ProductPermissions;

#[derive(Deserialize)]
struct CreateTraceBody {
    run_id: String,
    #[serde(default)]
    correlation_id: Option<String>,
    /// Payload for the initial `trace_started` event (required fields per [`validate_trace_started_payload`]).
    trace_started: Value,
}

#[derive(Deserialize)]
struct AppendEventBody {
    event_type: String,
    payload: Value,
    #[serde(default)]
    correlation_id: Option<String>,
}

#[derive(Deserialize)]
struct RecentQuery {
    #[serde(default = "default_limit")]
    limit: i64,
}

fn default_limit() -> i64 {
    20
}

fn api_err(
    status: StatusCode,
    code: &str,
    message: &str,
    hint: &str,
    details: Option<Value>,
) -> (StatusCode, Json<Value>) {
    api_error_with(status, code, message, hint, details, None)
}

async fn require_user(headers: &HeaderMap) -> Result<CurrentUser, (StatusCode, Json<Value>)> {
    let cfg = match AuthConfig::from_env() {
        Ok(c) => c,
        Err(e) => {
            return Err(api_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "CONFIG_ERROR",
                "Server authentication is not configured correctly.",
                "Contact support (this is a server-side configuration issue).",
                Some(json!({ "raw": e })),
            ))
        }
    };
    match crate::auth::require_user(&cfg, headers).await {
        Ok(u) => Ok(u),
        Err(resp) => Err(resp),
    }
}

async fn load_team_context(
    pool: &crate::db::DbPool,
    user: &CurrentUser,
    headers: &HeaderMap,
) -> Result<(Uuid, ProductPermissions), (StatusCode, Json<Value>)> {
    let team_id = resolve_team_id(pool, user, headers).await?;
    let perms = team_product_permissions(pool, team_id, user.user_id).await?;
    Ok((team_id, perms))
}

async fn ledger_tid_for_writes(
    pool: &crate::db::DbPool,
    team_id: Uuid,
) -> Result<String, (StatusCode, Json<Value>)> {
    match crate::product_ops::get_ledger_tenant_for_team(pool, team_id).await {
        Ok(Some(t)) if !t.trim().is_empty() => Ok(t),
        Ok(Some(_)) | Ok(None) => Err(api_err(
            StatusCode::BAD_REQUEST,
            "LEDGER_BINDING_REQUIRED",
            "Link this team to a ledger tenant before recording AI decision traces.",
            "POST /api/tenant-console/ledger-binding with ledger_tenant_id (admin).",
            None,
        )),
        Err(e) => Err(api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "DB_ERROR",
            "Could not read ledger binding.",
            "Retry. If this persists, contact support.",
            Some(json!({ "details": e.to_string() })),
        )),
    }
}

async fn ledger_tid_for_reads(
    pool: &crate::db::DbPool,
    team_id: Uuid,
) -> Result<Option<String>, (StatusCode, Json<Value>)> {
    match crate::product_ops::get_ledger_tenant_for_team(pool, team_id).await {
        Ok(x) => Ok(x),
        Err(e) => Err(api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "DB_ERROR",
            "Could not read ledger binding.",
            "Retry. If this persists, contact support.",
            Some(json!({ "details": e.to_string() })),
        )),
    }
}

async fn create_trace(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<CreateTraceBody>,
) -> (StatusCode, Json<Value>) {
    let user = match require_user(&headers).await {
        Ok(u) => u,
        Err(r) => return r,
    };
    let (team_id, perms) = match load_team_context(&state.pool, &user, &headers).await {
        Ok(x) => x,
        Err(r) => return r,
    };
    if !perms.ai_decision_trace_write {
        return (
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "error": {
                    "code": "INSUFFICIENT_ROLE",
                    "message": "You do not have permission to record AI decision traces.",
                    "hint": "Ask a team admin to grant a role with ai_decision_trace_write."
                },
                "required_permission": "ai_decision_trace_write"
            })),
        );
    }

    let run_id = match normalize_run_id(&body.run_id) {
        Ok(r) => r,
        Err(e) => {
            return api_err(
                StatusCode::BAD_REQUEST,
                "INVALID_RUN_ID",
                &e,
                "Provide a non-empty run_id under 256 characters.",
                None,
            )
        }
    };

    let ledger_tid = match ledger_tid_for_writes(&state.pool, team_id).await {
        Ok(t) => t,
        Err(r) => return r,
    };

    if let Err(e) = validate_trace_started_payload(&body.trace_started) {
        return api_err(
            StatusCode::BAD_REQUEST,
            "INVALID_TRACE_STARTED",
            &e,
            "See docs/ai-decision-audit for required trace_started fields.",
            None,
        );
    }

    let started = match trace_has_started_event(&state.pool, &ledger_tid, &run_id).await {
        Ok(b) => b,
        Err(e) => {
            return api_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "DB_ERROR",
                "Could not verify trace state.",
                "Retry.",
                Some(json!({ "details": e.to_string() })),
            )
        }
    };
    if started {
        return api_err(
            StatusCode::CONFLICT,
            "TRACE_ALREADY_EXISTS",
            "A trace_started event already exists for this run_id under this ledger tenant.",
            "Use POST /api/ai-decision-traces/{run_id}/events to append.",
            None,
        );
    }

    let correlation = body
        .correlation_id
        .as_deref()
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string());

    match insert_trace_event(
        &state.pool,
        &ledger_tid,
        Some(team_id),
        &run_id,
        correlation.as_deref(),
        "trace_started",
        body.trace_started.clone(),
    )
    .await
    {
        Ok(id) => {
            crate::runtime_metrics::inc_ai_trace_event();
            crate::ops_log::ai_trace_event_appended(
                "trace_started",
                "ledger_bound",
                correlation.is_some(),
            );
            (
                StatusCode::CREATED,
                Json(json!({
                    "ok": true,
                    "event_id": id.to_string(),
                    "ledger_tenant_id": ledger_tid,
                    "run_id": run_id,
                    "event_type": "trace_started"
                })),
            )
        }
        Err(e) => api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "DB_ERROR",
            "Could not persist trace_started.",
            "Retry.",
            Some(json!({ "details": e.to_string() })),
        ),
    }
}

async fn append_event(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(run_id): Path<String>,
    Json(body): Json<AppendEventBody>,
) -> (StatusCode, Json<Value>) {
    let user = match require_user(&headers).await {
        Ok(u) => u,
        Err(r) => return r,
    };
    let (team_id, perms) = match load_team_context(&state.pool, &user, &headers).await {
        Ok(x) => x,
        Err(r) => return r,
    };
    if !perms.ai_decision_trace_write {
        return (
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "error": {
                    "code": "INSUFFICIENT_ROLE",
                    "message": "You do not have permission to append AI decision trace events.",
                    "hint": "Ask a team admin to grant a role with ai_decision_trace_write."
                },
                "required_permission": "ai_decision_trace_write"
            })),
        );
    }

    let run_id = match normalize_run_id(&run_id) {
        Ok(r) => r,
        Err(e) => {
            return api_err(
                StatusCode::BAD_REQUEST,
                "INVALID_RUN_ID",
                &e,
                "Provide a valid run_id path segment.",
                None,
            )
        }
    };

    let ledger_tid = match ledger_tid_for_writes(&state.pool, team_id).await {
        Ok(t) => t,
        Err(r) => return r,
    };

    let et = body.event_type.trim();
    if et == "trace_started" {
        return api_err(
            StatusCode::BAD_REQUEST,
            "INVALID_EVENT_TYPE",
            "trace_started must be created via POST /api/ai-decision-traces.",
            "Use the create endpoint once per run_id.",
            None,
        );
    }

    if let Err(e) = validate_append_event(et, &body.payload) {
        return api_err(
            StatusCode::BAD_REQUEST,
            "INVALID_EVENT",
            &e,
            "See docs/ai-decision-audit for event payloads.",
            None,
        );
    }

    let started = match trace_has_started_event(&state.pool, &ledger_tid, &run_id).await {
        Ok(b) => b,
        Err(e) => {
            return api_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "DB_ERROR",
                "Could not verify trace state.",
                "Retry.",
                Some(json!({ "details": e.to_string() })),
            )
        }
    };
    if !started {
        return api_err(
            StatusCode::NOT_FOUND,
            "TRACE_NOT_FOUND",
            "No trace_started exists for this run_id under the current ledger tenant.",
            "Create the trace first via POST /api/ai-decision-traces.",
            None,
        );
    }

    if et == "completed" {
        let existing = match list_events_for_run_ordered(&state.pool, &ledger_tid, &run_id).await {
            Ok(e) => e,
            Err(e) => {
                return api_err(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "DB_ERROR",
                    "Could not load trace for verdict validation.",
                    "Retry.",
                    Some(json!({ "details": e.to_string() })),
                )
            }
        };
        let preview = preview_completed_verdict_detail(&existing, &body.payload);
        if preview.get("verdict_consistent").and_then(|v| v.as_bool()) != Some(true) {
            return api_err(
                StatusCode::BAD_REQUEST,
                "VERDICT_MISMATCH",
                "completed.final_audit_verdict must match the deterministic derivation from policy_eval events.",
                "Align final_audit_verdict with derived_audit_verdict from preview, or adjust policy_eval outcomes first.",
                Some(json!({ "verdict_preview": preview })),
            );
        }
    }

    let correlation = body
        .correlation_id
        .as_deref()
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string());

    match insert_trace_event(
        &state.pool,
        &ledger_tid,
        Some(team_id),
        &run_id,
        correlation.as_deref(),
        et,
        body.payload.clone(),
    )
    .await
    {
        Ok(id) => {
            crate::runtime_metrics::inc_ai_trace_event();
            crate::ops_log::ai_trace_event_appended(et, "ledger_bound", correlation.is_some());
            (
                StatusCode::OK,
                Json(json!({
                    "ok": true,
                    "event_id": id.to_string(),
                    "ledger_tenant_id": ledger_tid,
                    "run_id": run_id,
                    "event_type": et
                })),
            )
        }
        Err(e) => api_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "DB_ERROR",
            "Could not persist trace event.",
            "Retry.",
            Some(json!({ "details": e.to_string() })),
        ),
    }
}

type TraceReadResult = Result<(String, String, Vec<Value>), (StatusCode, Json<Value>)>;

pub(crate) async fn read_trace_events_bundle(
    pool: &crate::db::DbPool,
    headers: &HeaderMap,
    run_id_path: &str,
) -> TraceReadResult {
    let user = match require_user(headers).await {
        Ok(u) => u,
        Err(r) => return Err(r),
    };
    let (team_id, perms) = match load_team_context(pool, &user, headers).await {
        Ok(x) => x,
        Err(r) => return Err(r),
    };
    if !perms.ai_decision_trace_read {
        return Err((
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "error": {
                    "code": "INSUFFICIENT_ROLE",
                    "message": "You do not have permission to read AI decision traces.",
                    "hint": "Ask a team admin to grant a role with ai_decision_trace_read."
                },
                "required_permission": "ai_decision_trace_read"
            })),
        ));
    }

    let run_id = match normalize_run_id(run_id_path) {
        Ok(r) => r,
        Err(e) => {
            return Err(api_err(
                StatusCode::BAD_REQUEST,
                "INVALID_RUN_ID",
                &e,
                "Provide a valid run_id path segment.",
                None,
            ))
        }
    };

    let ledger_opt = match ledger_tid_for_reads(pool, team_id).await {
        Ok(x) => x,
        Err(r) => return Err(r),
    };
    let Some(ledger_tid) = ledger_opt else {
        return Err(api_err(
            StatusCode::NOT_FOUND,
            "LEDGER_NOT_BOUND",
            "This team has no ledger tenant binding; traces are unavailable.",
            "POST /api/tenant-console/ledger-binding first.",
            None,
        ));
    };

    let events = match list_events_for_run_ordered(pool, &ledger_tid, &run_id).await {
        Ok(e) => e,
        Err(e) => {
            return Err(api_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "DB_ERROR",
                "Could not load trace events.",
                "Retry.",
                Some(json!({ "details": e.to_string() })),
            ))
        }
    };

    if events.is_empty() {
        return Err(api_err(
            StatusCode::NOT_FOUND,
            "TRACE_NOT_FOUND",
            "No events for this run_id under the current ledger tenant.",
            "Create the trace via POST /api/ai-decision-traces.",
            None,
        ));
    }

    Ok((ledger_tid, run_id, events))
}

async fn get_trace(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(run_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    match read_trace_events_bundle(&state.pool, &headers, &run_id).await {
        Ok((ledger_tid, run_id, events)) => {
            let export = aggregate_trace_export(&ledger_tid, &run_id, &events);
            (
                StatusCode::OK,
                Json(json!({
                    "ok": true,
                    "contract_version": 2,
                    "ledger_tenant_id": ledger_tid,
                    "run_id": run_id,
                    "events": events,
                    "export": export
                })),
            )
        }
        Err(r) => r,
    }
}

async fn export_trace(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(run_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    match read_trace_events_bundle(&state.pool, &headers, &run_id).await {
        Ok((ledger_tid, run_id, events)) => {
            let export = aggregate_trace_export(&ledger_tid, &run_id, &events);
            (StatusCode::OK, Json(export))
        }
        Err(r) => r,
    }
}

async fn list_recent(
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(q): Query<RecentQuery>,
) -> (StatusCode, Json<Value>) {
    let user = match require_user(&headers).await {
        Ok(u) => u,
        Err(r) => return r,
    };
    let (team_id, perms) = match load_team_context(&state.pool, &user, &headers).await {
        Ok(x) => x,
        Err(r) => return r,
    };
    if !perms.ai_decision_trace_read {
        return (
            StatusCode::FORBIDDEN,
            Json(json!({
                "ok": false,
                "error": {
                    "code": "INSUFFICIENT_ROLE",
                    "message": "You do not have permission to list AI decision traces.",
                    "hint": "Ask a team admin to grant a role with ai_decision_trace_read."
                },
                "required_permission": "ai_decision_trace_read"
            })),
        );
    }

    let ledger_opt = match ledger_tid_for_reads(&state.pool, team_id).await {
        Ok(x) => x,
        Err(r) => return r,
    };
    let Some(ledger_tid) = ledger_opt else {
        return (
            StatusCode::OK,
            Json(json!({
                "ok": true,
                "contract_version": 1,
                "ledger_tenant_id": Value::Null,
                "recent_runs": [],
                "hint": "ledger_binding_required"
            })),
        );
    };

    let lim = q.limit.clamp(1, 100);
    let rows = match list_recent_run_summaries(&state.pool, &ledger_tid, lim).await {
        Ok(r) => r,
        Err(e) => {
            return api_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "DB_ERROR",
                "Could not list recent traces.",
                "Retry.",
                Some(json!({ "details": e.to_string() })),
            )
        }
    };

    (
        StatusCode::OK,
        Json(json!({
            "ok": true,
            "contract_version": 1,
            "ledger_tenant_id": ledger_tid,
            "recent_runs": rows
        })),
    )
}

pub fn router(pool: DbPool) -> Router {
    let state = AppState { pool };
    Router::new()
        .route("/api/ai-decision-traces/recent", get(list_recent))
        .route("/api/ai-decision-traces/:run_id/export", get(export_trace))
        .route("/api/ai-decision-traces/:run_id/events", post(append_event))
        .route("/api/ai-decision-traces/:run_id", get(get_trace))
        .route("/api/ai-decision-traces", post(create_trace))
        .with_state(state)
}
