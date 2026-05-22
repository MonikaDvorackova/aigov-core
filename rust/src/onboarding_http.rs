//! JWT-authenticated self-service onboarding HTTP routes.

use crate::auth::{require_user, AuthConfig};
use crate::db::DbPool;
use crate::govai_api::{json_error, resolve_team_id, AppState};
use crate::onboarding::{self, OnboardingCheckoutBody, ProvisionResult};
use crate::tenant_api_keys;
use axum::extract::{Path, State};
use axum::http::{HeaderMap, StatusCode};
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::Deserialize;
use serde_json::{json, Value};
use uuid::Uuid;

#[derive(Deserialize)]
pub struct ProvisionBody {
    pub organization_name: String,
}

#[derive(Deserialize)]
pub struct AdvanceBody {
    pub step: String,
}

#[derive(Deserialize)]
pub struct IssueKeyBody {
    #[serde(default = "default_key_label")]
    pub label: String,
}

fn default_key_label() -> String {
    "default".to_string()
}

#[derive(Deserialize)]
pub struct RotateKeyBody {
    pub label: Option<String>,
}

pub fn router(pool: DbPool) -> Router {
    Router::new()
        .route("/api/onboarding/status", get(onboarding_status))
        .route("/api/onboarding/provision", post(onboarding_provision))
        .route("/api/onboarding/advance", post(onboarding_advance))
        .route("/api/onboarding/api-keys", post(onboarding_issue_key))
        .route(
            "/api/onboarding/api-keys/:key_id/revoke",
            post(onboarding_revoke_key),
        )
        .route(
            "/api/onboarding/api-keys/:key_id/rotate",
            post(onboarding_rotate_key),
        )
        .route(
            "/api/onboarding/billing/checkout-session",
            post(onboarding_checkout_session),
        )
        .with_state(AppState { pool })
}

async fn auth_team(
    state: &AppState,
    headers: &HeaderMap,
) -> Result<(crate::auth::CurrentUser, Uuid), (StatusCode, Json<Value>)> {
    let cfg = AuthConfig::from_env().map_err(|e| {
        json_error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "config_error",
            "Server authentication is not configured correctly.",
            None,
            Some(json!({ "details": e })),
        )
    })?;
    let user = require_user(&cfg, headers).await.map_err(|r| r)?;
    let team_id = resolve_team_id(&state.pool, &user, headers).await?;
    Ok((user, team_id))
}

async fn onboarding_status(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> (StatusCode, Json<Value>) {
    let (_user, team_id) = match auth_team(&state, &headers).await {
        Ok(v) => v,
        Err(r) => return r,
    };
    match onboarding::get_onboarding_status(&state.pool, team_id).await {
        Ok(Some(s)) => (StatusCode::OK, Json(json!({ "ok": true, "onboarding": s }))),
        Ok(None) => (
            StatusCode::OK,
            Json(json!({
                "ok": true,
                "onboarding": null,
                "hint": "POST /api/onboarding/provision with organization_name to begin."
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

async fn onboarding_provision(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<ProvisionBody>,
) -> (StatusCode, Json<Value>) {
    let (user, _team_id) = match auth_team(&state, &headers).await {
        Ok(v) => v,
        Err(r) => return r,
    };
    let org = body.organization_name.trim();
    if org.is_empty() || org.len() > 256 {
        return json_error(
            StatusCode::BAD_REQUEST,
            "invalid_organization_name",
            "organization_name must be 1–256 characters.",
            None,
            None,
        );
    }
    match onboarding::provision_organization(&state.pool, user.user_id, org).await {
        Ok(ProvisionResult {
            team_id,
            organization_name,
            ledger_tenant_id,
            onboarding,
        }) => (
            StatusCode::OK,
            Json(json!({
                "ok": true,
                "team_id": team_id,
                "organization_name": organization_name,
                "ledger_tenant_id": ledger_tenant_id,
                "onboarding": onboarding,
            })),
        ),
        Err(e) => json_error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "provision_failed",
            "Could not provision organization tenant.",
            None,
            Some(json!({ "details": e.to_string() })),
        ),
    }
}

async fn onboarding_advance(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<AdvanceBody>,
) -> (StatusCode, Json<Value>) {
    let (_user, team_id) = match auth_team(&state, &headers).await {
        Ok(v) => v,
        Err(r) => return r,
    };
    match onboarding::advance_onboarding_step(&state.pool, team_id, body.step.trim()).await {
        Ok(Some(s)) => (StatusCode::OK, Json(json!({ "ok": true, "onboarding": s }))),
        Ok(None) => (
            StatusCode::NOT_FOUND,
            Json(json!({ "ok": false, "error": "onboarding_not_found" })),
        ),
        Err(e) => json_error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "db_error",
            "Could not update onboarding progress.",
            None,
            Some(json!({ "details": e.to_string() })),
        ),
    }
}

async fn onboarding_issue_key(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(_body): Json<IssueKeyBody>,
) -> (StatusCode, Json<Value>) {
    let (user, team_id) = match auth_team(&state, &headers).await {
        Ok(v) => v,
        Err(r) => return r,
    };
    match onboarding::issue_primary_api_key(&state.pool, team_id, user.user_id).await {
        Ok(Some((row, raw))) => (
            StatusCode::OK,
            Json(json!({
                "ok": true,
                "api_key": raw,
                "api_key_id": row.id.to_string(),
                "key_prefix": row.key_prefix,
                "ledger_tenant_id": row.ledger_tenant_id,
                "reveal_once": true,
                "warning": "Store this API key now. It cannot be retrieved again."
            })),
        ),
        Ok(None) => {
            let keys = tenant_api_keys::list_active_keys_for_team(&state.pool, team_id)
                .await
                .unwrap_or_default();
            (
                StatusCode::CONFLICT,
                Json(json!({
                    "ok": false,
                    "error": "api_key_already_issued",
                    "active_keys": keys.iter().map(|k| json!({
                        "id": k.id.to_string(),
                        "key_prefix": k.key_prefix,
                        "label": k.label,
                    })).collect::<Vec<_>>(),
                    "hint": "Use rotate to replace an existing key."
                })),
            )
        }
        Err(e) => json_error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "issue_key_failed",
            "Could not issue API key.",
            None,
            Some(json!({ "details": e.to_string() })),
        ),
    }
}

async fn onboarding_revoke_key(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(key_id): Path<Uuid>,
) -> (StatusCode, Json<Value>) {
    let (_user, team_id) = match auth_team(&state, &headers).await {
        Ok(v) => v,
        Err(r) => return r,
    };
    match tenant_api_keys::revoke_api_key(&state.pool, team_id, key_id).await {
        Ok(true) => (StatusCode::OK, Json(json!({ "ok": true, "revoked": true }))),
        Ok(false) => (
            StatusCode::NOT_FOUND,
            Json(json!({ "ok": false, "error": "key_not_found" })),
        ),
        Err(e) => json_error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "revoke_failed",
            "Could not revoke API key.",
            None,
            Some(json!({ "details": e.to_string() })),
        ),
    }
}

async fn onboarding_rotate_key(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(key_id): Path<Uuid>,
    Json(body): Json<RotateKeyBody>,
) -> (StatusCode, Json<Value>) {
    let (user, team_id) = match auth_team(&state, &headers).await {
        Ok(v) => v,
        Err(r) => return r,
    };
    let ledger: Option<String> = sqlx::query_scalar(
        r#"select ledger_tenant_id from public.govai_team_onboarding where team_id = $1"#,
    )
    .bind(team_id)
    .fetch_optional(&state.pool)
    .await
    .ok()
    .flatten();
    let Some(ledger_tid) = ledger else {
        return json_error(
            StatusCode::BAD_REQUEST,
            "onboarding_not_started",
            "Provision an organization before rotating keys.",
            None,
            None,
        );
    };
    let label = body
        .label
        .as_deref()
        .unwrap_or("default")
        .trim()
        .to_string();
    match tenant_api_keys::rotate_api_key(
        &state.pool,
        team_id,
        &ledger_tid,
        user.user_id,
        key_id,
        &label,
    )
    .await
    {
        Ok(Some((row, raw))) => (
            StatusCode::OK,
            Json(json!({
                "ok": true,
                "api_key": raw,
                "api_key_id": row.id.to_string(),
                "key_prefix": row.key_prefix,
                "reveal_once": true,
            })),
        ),
        Ok(None) => (
            StatusCode::NOT_FOUND,
            Json(json!({ "ok": false, "error": "key_not_found" })),
        ),
        Err(e) => json_error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "rotate_failed",
            "Could not rotate API key.",
            None,
            Some(json!({ "details": e.to_string() })),
        ),
    }
}

async fn onboarding_checkout_session(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(body): Json<OnboardingCheckoutBody>,
) -> (StatusCode, Json<Value>) {
    let (_user, team_id) = match auth_team(&state, &headers).await {
        Ok(v) => v,
        Err(r) => return r,
    };
    match onboarding::create_onboarding_checkout(&state.pool, team_id, &body).await {
        Ok((tenant_id, session_id, url)) => (
            StatusCode::OK,
            Json(json!({
                "ok": true,
                "tenant_id": tenant_id,
                "checkout_session_id": session_id,
                "checkout_url": url,
            })),
        ),
        Err(e) => {
            let code = if e.contains("STRIPE") || e.contains("stripe") {
                "STRIPE_NOT_CONFIGURED"
            } else {
                "checkout_failed"
            };
            json_error(
                StatusCode::SERVICE_UNAVAILABLE,
                code,
                &e,
                None,
                Some(json!({
                    "hint": "Configure GOVAI_STRIPE_SECRET_KEY and GOVAI_STRIPE_PRICE_PRO (Hosted Professional)."
                })),
            )
        }
    }
}
