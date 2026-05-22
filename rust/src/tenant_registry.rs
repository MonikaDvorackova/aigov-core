//! Hosted SaaS tenant registry: provisioning, onboarding progress, and persisted API keys.

use crate::api_usage::key_fingerprint;
use crate::audit_api_key;
use crate::db::DbPool;
use crate::stripe_billing;
use axum::http::HeaderMap;
use chrono::{DateTime, Utc};
use rand::RngCore;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sqlx::Row;
use uuid::Uuid;

/// Onboarding step keys aligned with `hosted-saas/onboarding-flow.json`.
pub const ONBOARDING_STEP_KEYS: &[&str] = &[
    "create_tenant",
    "invite_users",
    "configure_api_keys",
    "connect_audit_backend",
    "stream_audit_events",
    "review_compliance_summary",
    "export_audit_evidence",
];

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TenantRecord {
    pub id: Uuid,
    pub slug: String,
    pub display_name: String,
    pub status: String,
    pub plan: String,
    pub owner_user_id: Uuid,
    pub team_id: Uuid,
    pub ledger_tenant_id: String,
    pub stripe_customer_id: Option<String>,
    pub onboarding_status: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OnboardingStepRecord {
    pub step_key: String,
    pub completed: bool,
    pub completed_at: Option<DateTime<Utc>>,
    pub metadata: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TenantApiKeyRecord {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub prefix: String,
    pub scopes: Value,
    pub status: String,
    pub expires_at: Option<DateTime<Utc>>,
    pub last_used_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub revoked_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone)]
pub struct CreatedApiKey {
    pub record: TenantApiKeyRecord,
    pub plaintext: String,
}

pub fn sanitize_slug(input: &str) -> String {
    let lower = input.trim().to_lowercase();
    let mut out = String::new();
    let mut prev_hyphen = false;
    for ch in lower.chars() {
        if ch.is_ascii_alphanumeric() {
            out.push(ch);
            prev_hyphen = false;
        } else if !prev_hyphen {
            out.push('-');
            prev_hyphen = true;
        }
    }
    let trimmed = out.trim_matches('-');
    if trimmed.is_empty() {
        "tenant".to_string()
    } else {
        trimmed.chars().take(48).collect()
    }
}

pub fn ledger_tenant_id_for_uuid(tenant_id: Uuid) -> String {
    format!("ten_{}", tenant_id.as_simple())
}

pub fn generate_api_key_plaintext() -> String {
    let mut bytes = [0u8; 24];
    rand::thread_rng().fill_bytes(&mut bytes);
    format!("govai_sk_live_{}", hex::encode(bytes))
}

pub fn api_key_prefix(plaintext: &str) -> String {
    let t = plaintext.trim();
    if t.len() <= 16 {
        t.to_string()
    } else {
        format!("{}…", &t[..16])
    }
}

fn row_to_tenant(r: &sqlx::postgres::PgRow) -> TenantRecord {
    TenantRecord {
        id: r.get("id"),
        slug: r.get("slug"),
        display_name: r.get("display_name"),
        status: r.get("status"),
        plan: r.get("plan"),
        owner_user_id: r.get("owner_user_id"),
        team_id: r.get("team_id"),
        ledger_tenant_id: r.get("ledger_tenant_id"),
        stripe_customer_id: r.try_get("stripe_customer_id").ok().flatten(),
        onboarding_status: r.get("onboarding_status"),
        created_at: r.get("created_at"),
        updated_at: r.get("updated_at"),
    }
}

pub async fn slug_available(pool: &DbPool, slug: &str) -> Result<bool, sqlx::Error> {
    let n: Option<i64> = sqlx::query_scalar(
        r#"select 1::bigint from public.tenants where slug = $1 limit 1"#,
    )
    .bind(slug)
    .fetch_optional(pool)
    .await?;
    Ok(n.is_none())
}

pub async fn unique_slug(pool: &DbPool, base: &str) -> Result<String, sqlx::Error> {
    let candidate = sanitize_slug(base);
    if slug_available(pool, &candidate).await? {
        return Ok(candidate);
    }
    for i in 2..10_000 {
        let try_slug = format!("{candidate}-{i}");
        if slug_available(pool, &try_slug).await? {
            return Ok(try_slug);
        }
    }
    Ok(format!("{}-{}", candidate, Uuid::new_v4().as_simple()))
}

pub async fn user_can_access_tenant(
    pool: &DbPool,
    tenant_id: Uuid,
    user_id: Uuid,
) -> Result<bool, sqlx::Error> {
    let ok: Option<i64> = sqlx::query_scalar(
        r#"
        select 1::bigint
        from public.tenants t
        left join public.team_members tm on tm.team_id = t.team_id and tm.user_id = $2
        where t.id = $1 and (t.owner_user_id = $2 or tm.user_id is not null)
        limit 1
        "#,
    )
    .bind(tenant_id)
    .bind(user_id)
    .fetch_optional(pool)
    .await?;
    Ok(ok.is_some())
}

pub async fn get_tenant_by_id(pool: &DbPool, tenant_id: Uuid) -> Result<Option<TenantRecord>, sqlx::Error> {
    let row = sqlx::query(
        r#"
        select id, slug, display_name, status, plan, owner_user_id, team_id,
               ledger_tenant_id, stripe_customer_id, onboarding_status, created_at, updated_at
        from public.tenants where id = $1
        "#,
    )
    .bind(tenant_id)
    .fetch_optional(pool)
    .await?;
    Ok(row.as_ref().map(row_to_tenant))
}

pub async fn list_tenants_for_user(
    pool: &DbPool,
    user_id: Uuid,
) -> Result<Vec<TenantRecord>, sqlx::Error> {
    let rows = sqlx::query(
        r#"
        select distinct t.id, t.slug, t.display_name, t.status, t.plan, t.owner_user_id, t.team_id,
               t.ledger_tenant_id, t.stripe_customer_id, t.onboarding_status, t.created_at, t.updated_at
        from public.tenants t
        left join public.team_members tm on tm.team_id = t.team_id
        where t.owner_user_id = $1 or tm.user_id = $1
        order by t.created_at desc
        "#,
    )
    .bind(user_id)
    .fetch_all(pool)
    .await?;
    Ok(rows.iter().map(row_to_tenant).collect())
}

pub async fn initialize_onboarding(
    pool: &DbPool,
    tenant_id: Uuid,
    completed_steps: &[&str],
) -> Result<(), sqlx::Error> {
    for step in ONBOARDING_STEP_KEYS {
        let done = completed_steps.contains(step);
        sqlx::query(
            r#"
            insert into public.tenant_onboarding_progress (tenant_id, step_key, completed, completed_at, metadata)
            values ($1, $2, $3, case when $3 then now() else null end, '{}'::jsonb)
            on conflict (tenant_id, step_key) do update set
              completed = excluded.completed,
              completed_at = case when excluded.completed then coalesce(public.tenant_onboarding_progress.completed_at, now()) else null end
            "#,
        )
        .bind(tenant_id)
        .bind(*step)
        .bind(done)
        .execute(pool)
        .await?;
    }
    Ok(())
}

pub async fn get_onboarding_progress(
    pool: &DbPool,
    tenant_id: Uuid,
) -> Result<Vec<OnboardingStepRecord>, sqlx::Error> {
    let rows = sqlx::query(
        r#"
        select step_key, completed, completed_at, metadata
        from public.tenant_onboarding_progress
        where tenant_id = $1
        order by step_key
        "#,
    )
    .bind(tenant_id)
    .fetch_all(pool)
    .await?;
    Ok(rows
        .iter()
        .map(|r| OnboardingStepRecord {
            step_key: r.get("step_key"),
            completed: r.get("completed"),
            completed_at: r.try_get("completed_at").ok().flatten(),
            metadata: r.get("metadata"),
        })
        .collect())
}

pub async fn set_onboarding_step(
    pool: &DbPool,
    tenant_id: Uuid,
    step_key: &str,
    completed: bool,
    metadata: Value,
) -> Result<(), sqlx::Error> {
    if !ONBOARDING_STEP_KEYS.contains(&step_key) {
        return Err(sqlx::Error::Protocol(
            format!("unknown onboarding step_key: {step_key}").into(),
        ));
    }
    sqlx::query(
        r#"
        insert into public.tenant_onboarding_progress (tenant_id, step_key, completed, completed_at, metadata)
        values ($1, $2, $3, case when $3 then now() else null end, $4)
        on conflict (tenant_id, step_key) do update set
          completed = excluded.completed,
          completed_at = case when excluded.completed then now() else public.tenant_onboarding_progress.completed_at end,
          metadata = excluded.metadata
        "#,
    )
    .bind(tenant_id)
    .bind(step_key)
    .bind(completed)
    .bind(metadata)
    .execute(pool)
    .await?;

    let all_done = onboarding_all_complete(pool, tenant_id).await?;
    let status = if all_done { "completed" } else { "in_progress" };
    sqlx::query(
        r#"update public.tenants set onboarding_status = $2, updated_at = now() where id = $1"#,
    )
    .bind(tenant_id)
    .bind(status)
    .execute(pool)
    .await?;
    Ok(())
}

async fn onboarding_all_complete(pool: &DbPool, tenant_id: Uuid) -> Result<bool, sqlx::Error> {
    let pending: i64 = sqlx::query_scalar(
        r#"
        select count(*)::bigint from public.tenant_onboarding_progress
        where tenant_id = $1 and completed = false
        "#,
    )
    .bind(tenant_id)
    .fetch_one(pool)
    .await?;
    Ok(pending == 0)
}

#[derive(Debug, Clone)]
pub struct ProvisionTenantInput {
    pub owner_user_id: Uuid,
    pub display_name: String,
    pub slug: Option<String>,
    pub plan: String,
    pub create_api_key: bool,
    pub api_key_scopes: Value,
}

#[derive(Debug, Clone)]
pub struct ProvisionTenantResult {
    pub tenant: TenantRecord,
    pub api_key: Option<CreatedApiKey>,
}

/// Transactional hosted tenant provisioning (team, ledger binding, onboarding, billing).
pub async fn provision_tenant(
    pool: &DbPool,
    input: ProvisionTenantInput,
) -> Result<ProvisionTenantResult, String> {
    let slug = if let Some(s) = input.slug {
        let s = sanitize_slug(&s);
        if !slug_available(pool, &s)
            .await
            .map_err(|e| e.to_string())?
        {
            return Err(format!("slug_not_available:{s}"));
        }
        s
    } else {
        unique_slug(pool, &input.display_name)
            .await
            .map_err(|e| e.to_string())?
    };

    let tenant_id = Uuid::new_v4();
    let team_id = Uuid::new_v4();
    let ledger_tid = ledger_tenant_id_for_uuid(tenant_id);
    let team_name = format!("{} — GovBase", input.display_name.trim());

    let mut tx = pool.begin().await.map_err(|e| e.to_string())?;

    sqlx::query(r#"insert into public.teams (id, name) values ($1, $2)"#)
        .bind(team_id)
        .bind(&team_name)
        .execute(&mut *tx)
        .await
        .map_err(|e| e.to_string())?;

    sqlx::query(
        r#"insert into public.team_members (team_id, user_id, role) values ($1, $2, 'owner')"#,
    )
    .bind(team_id)
    .bind(input.owner_user_id)
    .execute(&mut *tx)
    .await
    .map_err(|e| e.to_string())?;

    sqlx::query(
        r#"
        insert into public.tenants (
          id, slug, display_name, status, plan, owner_user_id, team_id,
          ledger_tenant_id, onboarding_status
        ) values ($1, $2, $3, 'active', $4, $5, $6, $7, 'in_progress')
        "#,
    )
    .bind(tenant_id)
    .bind(&slug)
    .bind(input.display_name.trim())
    .bind(input.plan.trim())
    .bind(input.owner_user_id)
    .bind(team_id)
    .bind(&ledger_tid)
    .execute(&mut *tx)
    .await
    .map_err(|e| e.to_string())?;

    sqlx::query(
        r#"
        insert into public.govai_team_ledger_bindings (team_id, ledger_tenant_id)
        values ($1, $2)
        on conflict (team_id) do update set ledger_tenant_id = excluded.ledger_tenant_id
        "#,
    )
    .bind(team_id)
    .bind(&ledger_tid)
    .execute(&mut *tx)
    .await
    .map_err(|e| e.to_string())?;

    tx.commit().await.map_err(|e| e.to_string())?;

    initialize_onboarding(pool, tenant_id, &["create_tenant"])
        .await
        .map_err(|e| e.to_string())?;

    stripe_billing::upsert_tenant_billing_account(
        pool,
        &ledger_tid,
        None,
        None,
        None,
        "none",
        None,
        None,
    )
    .await
    .map_err(|e| e.to_string())?;

    let tenant = get_tenant_by_id(pool, tenant_id)
        .await
        .map_err(|e| e.to_string())?
        .ok_or_else(|| "tenant_missing_after_insert".to_string())?;

    let api_key = if input.create_api_key {
        Some(
            create_initial_api_key(pool, tenant_id, input.api_key_scopes)
                .await?,
        )
    } else {
        None
    };

    if let Some(ref key) = api_key {
        audit_api_key::register_runtime_api_key(&key.plaintext, &ledger_tid)?;
        let _ = set_onboarding_step(
            pool,
            tenant_id,
            "configure_api_keys",
            true,
            json!({ "prefix": key.record.prefix }),
        )
        .await;
    }

    Ok(ProvisionTenantResult { tenant, api_key })
}

pub async fn create_initial_api_key(
    pool: &DbPool,
    tenant_id: Uuid,
    scopes: Value,
) -> Result<CreatedApiKey, String> {
    let _tenant = get_tenant_by_id(pool, tenant_id)
        .await
        .map_err(|e| e.to_string())?
        .ok_or_else(|| "tenant_not_found".to_string())?;

    let plaintext = generate_api_key_plaintext();
    let hash = key_fingerprint(&plaintext);
    let prefix = api_key_prefix(&plaintext);
    let id = Uuid::new_v4();

    sqlx::query(
        r#"
        insert into public.tenant_api_keys (id, tenant_id, key_hash, prefix, scopes, status)
        values ($1, $2, $3, $4, $5, 'active')
        "#,
    )
    .bind(id)
    .bind(tenant_id)
    .bind(&hash)
    .bind(&prefix)
    .bind(&scopes)
    .execute(pool)
    .await
    .map_err(|e| e.to_string())?;

    let record = TenantApiKeyRecord {
        id,
        tenant_id,
        prefix,
        scopes,
        status: "active".to_string(),
        expires_at: None,
        last_used_at: None,
        created_at: Utc::now(),
        revoked_at: None,
    };

    Ok(CreatedApiKey {
        record,
        plaintext,
    })
}

pub async fn list_api_keys_for_tenant(
    pool: &DbPool,
    tenant_id: Uuid,
) -> Result<Vec<TenantApiKeyRecord>, sqlx::Error> {
    let rows = sqlx::query(
        r#"
        select id, tenant_id, prefix, scopes, status, expires_at, last_used_at, created_at, revoked_at
        from public.tenant_api_keys
        where tenant_id = $1
        order by created_at desc
        "#,
    )
    .bind(tenant_id)
    .fetch_all(pool)
    .await?;
    Ok(rows
        .iter()
        .map(|r| TenantApiKeyRecord {
            id: r.get("id"),
            tenant_id: r.get("tenant_id"),
            prefix: r.get("prefix"),
            scopes: r.get("scopes"),
            status: r.get("status"),
            expires_at: r.try_get("expires_at").ok().flatten(),
            last_used_at: r.try_get("last_used_at").ok().flatten(),
            created_at: r.get("created_at"),
            revoked_at: r.try_get("revoked_at").ok().flatten(),
        })
        .collect())
}

pub async fn revoke_api_key(
    pool: &DbPool,
    tenant_id: Uuid,
    key_id: Uuid,
) -> Result<bool, sqlx::Error> {
    let res = sqlx::query(
        r#"
        update public.tenant_api_keys
        set status = 'revoked', revoked_at = now()
        where id = $1 and tenant_id = $2 and status = 'active'
        "#,
    )
    .bind(key_id)
    .bind(tenant_id)
    .execute(pool)
    .await?;
    Ok(res.rows_affected() > 0)
}

/// Resolve ledger tenant id from bearer token using in-memory map then database hash lookup.
pub async fn ledger_tenant_for_key_hash(
    pool: &DbPool,
    key_hash: &str,
) -> Result<Option<String>, sqlx::Error> {
    sqlx::query_scalar(
        r#"
        select t.ledger_tenant_id
        from public.tenant_api_keys k
        join public.tenants t on t.id = k.tenant_id
        where k.key_hash = $1
          and k.status = 'active'
          and (k.expires_at is null or k.expires_at > now())
          and t.status = 'active'
        limit 1
        "#,
    )
    .bind(key_hash)
    .fetch_optional(pool)
    .await
}

pub async fn resolve_ledger_tenant_from_headers(
    headers: &HeaderMap,
    deployment_env: crate::govai_environment::GovaiEnvironment,
    pool: Option<&DbPool>,
) -> Option<String> {
    if let Ok(tid) =
        audit_api_key::require_tenant_id_from_api_key_for_ledger(headers, deployment_env)
    {
        return Some(tid);
    }
    let token = audit_api_key::raw_bearer_token(headers)?;
    let pool = pool?;
    let hash = key_fingerprint(token);
    ledger_tenant_for_key_hash(pool, &hash)
        .await
        .ok()
        .flatten()
}

pub async fn touch_api_key_last_used(pool: &DbPool, key_hash: &str) {
    let _ = sqlx::query(
        r#"update public.tenant_api_keys set last_used_at = now() where key_hash = $1 and status = 'active'"#,
    )
    .bind(key_hash)
    .execute(pool)
    .await;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sanitize_slug_normalizes() {
        assert_eq!(sanitize_slug("  Acme Corp!  "), "acme-corp");
    }

    #[test]
    fn ledger_tenant_id_is_stable() {
        let id = Uuid::parse_str("550e8400-e29b-41d4-a716-446655440000").unwrap();
        assert_eq!(
            ledger_tenant_id_for_uuid(id),
            "ten_550e8400e29b41d4a716446655440000"
        );
    }
}
