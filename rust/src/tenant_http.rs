//! JWT-authenticated hosted SaaS tenant registry HTTP API.

use crate::auth::{AuthConfig, CurrentUser};
use crate::db::DbPool;
use crate::tenant_registry::{
    self, CreatedApiKey, OnboardingStepRecord, ProvisionTenantInput, TenantApiKeyRecord, TenantRecord,
};
use axum::extract::{Path, State};
use axum::http::{HeaderMap, StatusCode};
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use uuid::Uuid;

#[derive(Clone)]
pub struct TenantHttpState {
    pub pool: DbPool,
}

#[derive(Deserialize)]
pub struct CreateTenantBody {
    pub display_name: String,
    pub slug: Option<String>,
    pub plan: Option<String>,
    pub create_api_key: Option<bool>,
    pub api_key_scopes: Option<Value>,
}

#[derive(Deserialize)]
pub struct CreateApiKeyBody {
    pub scopes: Option<Value>,
}

#[derive(Deserialize)]
pub struct PatchOnboardingBody {
    pub step_key: String,
    pub completed: bool,
    pub metadata: Option<Value>,
}

#[derive(Serialize)]
pub struct TenantOut {
    pub id: String,
    pub slug: String,
    pub display_name: String,
    pub status: String,
    pub plan: String,
    pub owner_user_id: String,
    pub team_id: String,
    pub ledger_tenant_id: String,
    pub stripe_customer_id: Option<String>,
    pub onboarding_status: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Serialize)]
pub struct ApiKeyOut {
    pub id: String,
    pub tenant_id: String,
    pub prefix: String,
    pub scopes: Value,
    pub status: String,
    pub expires_at: Option<String>,
    pub last_used_at: Option<String>,
    pub created_at: String,
    pub revoked_at: Option<String>,
}

fn tenant_to_out(t: &TenantRecord) -> TenantOut {
    TenantOut {
        id: t.id.to_string(),
        slug: t.slug.clone(),
        display_name: t.display_name.clone(),
        status: t.status.clone(),
        plan: t.plan.clone(),
        owner_user_id: t.owner_user_id.to_string(),
        team_id: t.team_id.to_string(),
        ledger_tenant_id: t.ledger_tenant_id.clone(),
        stripe_customer_id: t.stripe_customer_id.clone(),
        onboarding_status: t.onboarding_status.clone(),
        created_at: t.created_at.to_rfc3339(),
        updated_at: t.updated_at.to_rfc3339(),
    }
}

fn api_key_to_out(k: &TenantApiKeyRecord) -> ApiKeyOut {
    ApiKeyOut {
        id: k.id.to_string(),
        tenant_id: k.tenant_id.to_string(),
        prefix: k.prefix.clone(),
        scopes: k.scopes.clone(),
        status: k.status.clone(),
        expires_at: k.expires_at.map(|d| d.to_rfc3339()),
        last_used_at: k.last_used_at.map(|d| d.to_rfc3339()),
        created_at: k.created_at.to_rfc3339(),
        revoked_at: k.revoked_at.map(|d| d.to_rfc3339()),
    }
}

fn json_ok(body: Value) -> (StatusCode, Json<Value>) {
    (StatusCode::OK, Json(body))
}

fn json_err(
    status: StatusCode,
    code: &str,
    message: &str,
    details: Option<Value>,
) -> (StatusCode, Json<Value>) {
    (
        status,
        Json(json!({
            "ok": false,
            "error": code,
            "code": code,
            "message": message,
            "details": details
        })),
    )
}

async fn auth_user(
    headers: &HeaderMap,
) -> Result<CurrentUser, (StatusCode, Json<Value>)> {
    let cfg = AuthConfig::from_env().map_err(|e| {
        json_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "config_error",
            "Server authentication is not configured correctly.",
            Some(json!({ "raw": e })),
        )
    })?;
    crate::auth::require_user(&cfg, headers)
        .await
        .map_err(|(status, json)| (status, Json(json.0)))
}

async fn require_tenant_access(
    pool: &DbPool,
    tenant_id: Uuid,
    user_id: Uuid,
) -> Result<(), (StatusCode, Json<Value>)> {
    let ok = tenant_registry::user_can_access_tenant(pool, tenant_id, user_id)
        .await
        .map_err(|e| {
            json_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "We could not verify tenant access.",
                Some(json!({ "raw": e.to_string() })),
            )
        })?;
    if ok {
        Ok(())
    } else {
        Err(json_err(
            StatusCode::FORBIDDEN,
            "forbidden",
            "You do not have access to this tenant.",
            None,
        ))
    }
}

async fn create_tenant(
    State(state): State<TenantHttpState>,
    headers: HeaderMap,
    Json(body): Json<CreateTenantBody>,
) -> (StatusCode, Json<Value>) {
    let user = match auth_user(&headers).await {
        Ok(u) => u,
        Err(r) => return r,
    };

    let display_name = body.display_name.trim();
    if display_name.is_empty() {
        return json_err(
            StatusCode::BAD_REQUEST,
            "invalid_display_name",
            "display_name is required.",
            None,
        );
    }

    let plan = body
        .plan
        .unwrap_or_else(|| "developer".to_string())
        .trim()
        .to_string();
    let scopes = body.api_key_scopes.unwrap_or_else(|| json!([]));
    let create_key = body.create_api_key.unwrap_or(true);

    let result = match tenant_registry::provision_tenant(
        &state.pool,
        ProvisionTenantInput {
            owner_user_id: user.user_id,
            display_name: display_name.to_string(),
            slug: body.slug,
            plan,
            create_api_key: create_key,
            api_key_scopes: scopes,
        },
    )
    .await
    {
        Ok(r) => r,
        Err(e) => {
            if e.starts_with("slug_not_available:") {
                return json_err(
                    StatusCode::CONFLICT,
                    "slug_not_available",
                    "That tenant slug is already taken.",
                    Some(json!({ "raw": e })),
                );
            }
            return json_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "provision_failed",
                "Tenant provisioning failed.",
                Some(json!({ "raw": e })),
            );
        }
    };

    let mut payload = json!({
        "ok": true,
        "tenant": tenant_to_out(&result.tenant),
    });
    if let Some(ref key) = result.api_key {
        if let serde_json::Value::Object(ref mut map) = payload {
            map.insert(
                "api_key".to_string(),
                json!({
                    "id": key.record.id.to_string(),
                    "prefix": key.record.prefix,
                    "plaintext": key.plaintext,
                    "scopes": key.record.scopes,
                    "warning": "Store this API key now. It will not be shown again."
                }),
            );
        }
    }

    (StatusCode::CREATED, Json(payload))
}

async fn list_tenants(
    State(state): State<TenantHttpState>,
    headers: HeaderMap,
) -> (StatusCode, Json<Value>) {
    let user = match auth_user(&headers).await {
        Ok(u) => u,
        Err(r) => return r,
    };

    let tenants = match tenant_registry::list_tenants_for_user(&state.pool, user.user_id).await {
        Ok(t) => t,
        Err(e) => {
            return json_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "We could not list tenants.",
                Some(json!({ "raw": e.to_string() })),
            )
        }
    };

    json_ok(json!({
        "ok": true,
        "tenants": tenants.iter().map(tenant_to_out).collect::<Vec<_>>()
    }))
}

async fn get_tenant(
    State(state): State<TenantHttpState>,
    headers: HeaderMap,
    Path(tenant_id): Path<Uuid>,
) -> (StatusCode, Json<Value>) {
    let user = match auth_user(&headers).await {
        Ok(u) => u,
        Err(r) => return r,
    };

    if let Err(r) = require_tenant_access(&state.pool, tenant_id, user.user_id).await {
        return r;
    }

    let tenant = match tenant_registry::get_tenant_by_id(&state.pool, tenant_id).await {
        Ok(Some(t)) => t,
        Ok(None) => {
            return json_err(
                StatusCode::NOT_FOUND,
                "not_found",
                "Tenant not found.",
                None,
            )
        }
        Err(e) => {
            return json_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "We could not load the tenant.",
                Some(json!({ "raw": e.to_string() })),
            )
        }
    };

    json_ok(json!({
        "ok": true,
        "tenant": tenant_to_out(&tenant)
    }))
}

async fn get_onboarding(
    State(state): State<TenantHttpState>,
    headers: HeaderMap,
    Path(tenant_id): Path<Uuid>,
) -> (StatusCode, Json<Value>) {
    let user = match auth_user(&headers).await {
        Ok(u) => u,
        Err(r) => return r,
    };

    if let Err(r) = require_tenant_access(&state.pool, tenant_id, user.user_id).await {
        return r;
    }

    let tenant = match tenant_registry::get_tenant_by_id(&state.pool, tenant_id).await {
        Ok(Some(t)) => t,
        Ok(None) => {
            return json_err(StatusCode::NOT_FOUND, "not_found", "Tenant not found.", None)
        }
        Err(e) => {
            return json_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "We could not load the tenant.",
                Some(json!({ "raw": e.to_string() })),
            )
        }
    };

    let steps = match tenant_registry::get_onboarding_progress(&state.pool, tenant_id).await {
        Ok(s) => s,
        Err(e) => {
            return json_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "We could not load onboarding progress.",
                Some(json!({ "raw": e.to_string() })),
            )
        }
    };

    let keys = match tenant_registry::list_api_keys_for_tenant(&state.pool, tenant_id).await {
        Ok(k) => k,
        Err(e) => {
            return json_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "We could not load API keys.",
                Some(json!({ "raw": e.to_string() })),
            )
        }
    };

    json_ok(json!({
        "ok": true,
        "tenant": tenant_to_out(&tenant),
        "onboarding_status": tenant.onboarding_status,
        "steps": steps.iter().map(onboarding_step_json).collect::<Vec<_>>(),
        "api_keys": keys.iter().map(api_key_to_out).collect::<Vec<_>>(),
    }))
}

fn onboarding_step_json(s: &OnboardingStepRecord) -> Value {
    json!({
        "step_key": s.step_key,
        "completed": s.completed,
        "completed_at": s.completed_at.map(|d| d.to_rfc3339()),
        "metadata": s.metadata,
    })
}

async fn patch_onboarding(
    State(state): State<TenantHttpState>,
    headers: HeaderMap,
    Path(tenant_id): Path<Uuid>,
    Json(body): Json<PatchOnboardingBody>,
) -> (StatusCode, Json<Value>) {
    let user = match auth_user(&headers).await {
        Ok(u) => u,
        Err(r) => return r,
    };

    if let Err(r) = require_tenant_access(&state.pool, tenant_id, user.user_id).await {
        return r;
    }

    let metadata = body.metadata.unwrap_or_else(|| json!({}));
    if let Err(e) = tenant_registry::set_onboarding_step(
        &state.pool,
        tenant_id,
        &body.step_key,
        body.completed,
        metadata,
    )
    .await
    {
        let msg = e.to_string();
        if msg.contains("unknown onboarding step_key") {
            return json_err(
                StatusCode::BAD_REQUEST,
                "invalid_step_key",
                "Unknown onboarding step key.",
                Some(json!({ "raw": msg })),
            );
        }
        return json_err(
            StatusCode::INTERNAL_SERVER_ERROR,
            "db_error",
            "We could not update onboarding progress.",
            Some(json!({ "raw": msg })),
        );
    }

    get_onboarding(State(state), headers, Path(tenant_id)).await
}

async fn create_api_key(
    State(state): State<TenantHttpState>,
    headers: HeaderMap,
    Path(tenant_id): Path<Uuid>,
    Json(body): Json<CreateApiKeyBody>,
) -> (StatusCode, Json<Value>) {
    let user = match auth_user(&headers).await {
        Ok(u) => u,
        Err(r) => return r,
    };

    if let Err(r) = require_tenant_access(&state.pool, tenant_id, user.user_id).await {
        return r;
    }

    let scopes = body.scopes.unwrap_or_else(|| json!([]));
    let CreatedApiKey { record, plaintext } =
        match tenant_registry::create_initial_api_key(&state.pool, tenant_id, scopes).await {
            Ok(k) => k,
            Err(e) => {
                return json_err(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "api_key_create_failed",
                    "We could not create an API key.",
                    Some(json!({ "raw": e })),
                )
            }
        };

    if let Ok(tenant) = tenant_registry::get_tenant_by_id(&state.pool, tenant_id).await {
        if let Some(tenant) = tenant {
            let _ = crate::audit_api_key::register_runtime_api_key(&plaintext, &tenant.ledger_tenant_id);
            let _ = tenant_registry::set_onboarding_step(
                &state.pool,
                tenant_id,
                "configure_api_keys",
                true,
                json!({ "prefix": record.prefix }),
            )
            .await;
        }
    }

    (
        StatusCode::CREATED,
        Json(json!({
            "ok": true,
            "api_key": api_key_to_out(&record),
            "plaintext": plaintext,
            "warning": "Store this API key now. It will not be shown again."
        })),
    )
}

async fn revoke_api_key(
    State(state): State<TenantHttpState>,
    headers: HeaderMap,
    Path((tenant_id, key_id)): Path<(Uuid, Uuid)>,
) -> (StatusCode, Json<Value>) {
    let user = match auth_user(&headers).await {
        Ok(u) => u,
        Err(r) => return r,
    };

    if let Err(r) = require_tenant_access(&state.pool, tenant_id, user.user_id).await {
        return r;
    }

    let revoked = match tenant_registry::revoke_api_key(&state.pool, tenant_id, key_id).await {
        Ok(b) => b,
        Err(e) => {
            return json_err(
                StatusCode::INTERNAL_SERVER_ERROR,
                "db_error",
                "We could not revoke the API key.",
                Some(json!({ "raw": e.to_string() })),
            )
        }
    };

    if !revoked {
        return json_err(
            StatusCode::NOT_FOUND,
            "not_found",
            "Active API key not found for this tenant.",
            None,
        );
    }

    json_ok(json!({ "ok": true, "revoked": true, "key_id": key_id.to_string() }))
}

pub fn router(pool: DbPool) -> Router {
    let state = TenantHttpState { pool };
    Router::new()
        .route("/api/tenants", post(create_tenant).get(list_tenants))
        .route("/api/tenants/:tenant_id", get(get_tenant))
        .route(
            "/api/tenants/:tenant_id/onboarding",
            get(get_onboarding).patch(axum::routing::patch(patch_onboarding)),
        )
        .route("/api/tenants/:tenant_id/api-keys", post(create_api_key))
        .route(
            "/api/tenants/:tenant_id/api-keys/:key_id/revoke",
            post(revoke_api_key),
        )
        .with_state(state)
}
