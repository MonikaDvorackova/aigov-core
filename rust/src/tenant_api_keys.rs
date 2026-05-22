//! Database-backed API keys for self-service customers (hash-only storage).

use crate::api_usage::key_fingerprint;
use crate::audit_api_key;
use crate::db::DbPool;
use crate::govai_environment::GovaiEnvironment;
use axum::http::HeaderMap;
use sqlx::Row;
use uuid::Uuid;

const KEY_PREFIX: &str = "govai_live_";

#[derive(Debug, Clone)]
pub struct IssuedKeyRow {
    pub id: Uuid,
    pub ledger_tenant_id: String,
    pub team_id: Uuid,
    pub key_prefix: String,
    pub label: String,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub revoked_at: Option<chrono::DateTime<chrono::Utc>>,
    pub revealed_at: Option<chrono::DateTime<chrono::Utc>>,
}

fn generate_raw_api_key() -> String {
    format!("{}{}", KEY_PREFIX, uuid::Uuid::new_v4().simple())
}

/// Resolve ledger tenant from bearer token: env map first, then DB-issued keys.
pub async fn resolve_ledger_tenant_for_bearer(
    pool: &DbPool,
    headers: &HeaderMap,
    deployment_env: GovaiEnvironment,
) -> Result<String, String> {
    let token = audit_api_key::raw_bearer_token(headers).ok_or_else(|| "missing_api_key".to_string())?;

    if audit_api_key::env_tenant_map_contains_token(token) {
        return audit_api_key::require_tenant_id_from_api_key_for_ledger(headers, deployment_env);
    }

    if let Some(tid) = lookup_tenant_by_key_hash(pool, token)
        .await
        .map_err(|e| format!("db_key_lookup: {e}"))?
    {
        return Ok(tid);
    }

    match deployment_env {
        GovaiEnvironment::Dev if !audit_api_key::api_key_tenant_map_is_initialized() => {
            Ok("default".to_string())
        }
        _ => Err("unknown_api_key".to_string()),
    }
}

async fn lookup_tenant_by_key_hash(
    pool: &DbPool,
    raw_token: &str,
) -> Result<Option<String>, sqlx::Error> {
    let hash = key_fingerprint(raw_token);
    let row: Option<(String,)> = sqlx::query_as(
        r#"
        select ledger_tenant_id
        from public.govai_issued_api_keys
        where key_hash = $1 and revoked_at is null
        limit 1
        "#,
    )
    .bind(&hash)
    .fetch_optional(pool)
    .await?;
    Ok(row.map(|r| r.0))
}

/// Whether the bearer token is authorized for audit routes (env allowlist or active issued key).
pub async fn bearer_token_is_authorized(
    pool: &DbPool,
    token: &str,
    deployment_env: GovaiEnvironment,
) -> bool {
    if token.is_empty() {
        return false;
    }
    if audit_api_key::env_tenant_map_contains_token(token) {
        return true;
    }
    if audit_api_key::env_allowlist_contains_token(token) {
        return true;
    }
    match lookup_tenant_by_key_hash(pool, token).await {
        Ok(Some(_)) => true,
        Ok(None) => {
            deployment_env == GovaiEnvironment::Dev
                && !audit_api_key::api_key_tenant_map_is_initialized()
                && audit_api_key::AuditApiKeyConfig::from_env().keys.is_none()
        }
        Err(_) => false,
    }
}

pub async fn issue_api_key(
    pool: &DbPool,
    team_id: Uuid,
    ledger_tenant_id: &str,
    created_by: Uuid,
    label: &str,
) -> Result<(IssuedKeyRow, String), sqlx::Error> {
    let raw = generate_raw_api_key();
    let hash = key_fingerprint(&raw);
    let prefix = raw.chars().take(12).collect::<String>();
    let id = Uuid::new_v4();

    sqlx::query(
        r#"
        insert into public.govai_issued_api_keys (
          id, ledger_tenant_id, team_id, key_hash, key_prefix, label, created_by, revealed_at
        )
        values ($1, $2, $3, $4, $5, $6, $7, now())
        "#,
    )
    .bind(id)
    .bind(ledger_tenant_id)
    .bind(team_id)
    .bind(&hash)
    .bind(&prefix)
    .bind(label)
    .bind(created_by)
    .execute(pool)
    .await?;

    let row = IssuedKeyRow {
        id,
        ledger_tenant_id: ledger_tenant_id.to_string(),
        team_id,
        key_prefix: prefix,
        label: label.to_string(),
        created_at: chrono::Utc::now(),
        revoked_at: None,
        revealed_at: Some(chrono::Utc::now()),
    };
    Ok((row, raw))
}

pub async fn revoke_api_key(
    pool: &DbPool,
    team_id: Uuid,
    key_id: Uuid,
) -> Result<bool, sqlx::Error> {
    let r = sqlx::query(
        r#"
        update public.govai_issued_api_keys
        set revoked_at = now()
        where id = $1 and team_id = $2 and revoked_at is null
        "#,
    )
    .bind(key_id)
    .bind(team_id)
    .execute(pool)
    .await?;
    Ok(r.rows_affected() > 0)
}

pub async fn list_active_keys_for_team(
    pool: &DbPool,
    team_id: Uuid,
) -> Result<Vec<IssuedKeyRow>, sqlx::Error> {
    let rows = sqlx::query(
        r#"
        select id, ledger_tenant_id, team_id, key_prefix, label, created_at, revoked_at, revealed_at
        from public.govai_issued_api_keys
        where team_id = $1 and revoked_at is null
        order by created_at desc
        "#,
    )
    .bind(team_id)
    .fetch_all(pool)
    .await?;

    Ok(rows
        .into_iter()
        .map(|r| IssuedKeyRow {
            id: r.get("id"),
            ledger_tenant_id: r.get("ledger_tenant_id"),
            team_id: r.get("team_id"),
            key_prefix: r.get("key_prefix"),
            label: r.get("label"),
            created_at: r.get("created_at"),
            revoked_at: r.get("revoked_at"),
            revealed_at: r.get("revealed_at"),
        })
        .collect())
}

pub async fn rotate_api_key(
    pool: &DbPool,
    team_id: Uuid,
    ledger_tenant_id: &str,
    created_by: Uuid,
    old_key_id: Uuid,
    label: &str,
) -> Result<Option<(IssuedKeyRow, String)>, sqlx::Error> {
    if !revoke_api_key(pool, team_id, old_key_id).await? {
        return Ok(None);
    }
    let (row, raw) = issue_api_key(pool, team_id, ledger_tenant_id, created_by, label).await?;
    Ok(Some((row, raw)))
}

/// Assert no plaintext secrets are persisted (test helper).
pub async fn count_plaintext_key_violations(pool: &DbPool) -> Result<i64, sqlx::Error> {
    let n: i64 = sqlx::query_scalar(
        r#"
        select count(*)::bigint
        from public.govai_issued_api_keys
        where key_hash !~ '^[0-9a-f]{64}$'
        "#,
    )
    .fetch_one(pool)
    .await?;
    Ok(n)
}
