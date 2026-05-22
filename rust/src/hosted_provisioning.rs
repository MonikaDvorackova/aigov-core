//! Hosted self-service tenant provisioning: API key issuance, ledger binding, onboarding state.
//!
//! Enabled when `GOVAI_HOSTED_SELF_SERVICE=on`. Complements operator env keys (`GOVAI_API_KEYS_JSON`).

use crate::api_usage::key_fingerprint;
use crate::audit_api_key;
use crate::db::DbPool;
use crate::product_ops;
use sqlx::Row;
use uuid::Uuid;

pub async fn reload_hosted_api_keys_from_db(pool: &DbPool) -> Result<usize, sqlx::Error> {
    if !audit_api_key::hosted_self_service_enabled() {
        return Ok(0);
    }
    let rows = sqlx::query(
        r#"
        select key_hash, ledger_tenant_id
        from public.govai_hosted_api_keys
        where revoked_at is null
        "#,
    )
    .fetch_all(pool)
    .await?;

    let mut count = 0_usize;
    for row in rows {
        let hash: String = row.get("key_hash");
        let tenant: String = row.get("ledger_tenant_id");
        audit_api_key::register_hosted_key_hash(&hash, &tenant);
        count += 1;
    }
    Ok(count)
}

fn generate_api_key_secret() -> String {
    let a = Uuid::new_v4().to_string().replace('-', "");
    let b = Uuid::new_v4().to_string().replace('-', "");
    format!("govai_live_{a}{b}")
}

pub struct ProvisionResult {
    pub team_id: Uuid,
    pub ledger_tenant_id: String,
    pub api_key: String,
    pub key_prefix: String,
    pub reused_existing: bool,
}

pub async fn provision_team(
    pool: &DbPool,
    team_id: Uuid,
    user_id: Uuid,
) -> Result<ProvisionResult, String> {
    if !audit_api_key::hosted_self_service_enabled() {
        return Err("hosted_self_service_disabled".into());
    }

    if let Some(existing) = active_hosted_key_for_team(pool, team_id)
        .await
        .map_err(|e| e.to_string())?
    {
        return Err(format!(
            "api_key_already_issued:prefix={}",
            existing.key_prefix
        ));
    }

    let ledger_tenant_id = format!("lt-{team_id}");
    let api_key = generate_api_key_secret();
    let key_hash = key_fingerprint(&api_key);
    let key_prefix = api_key.chars().take(16).collect::<String>() + "…";

    sqlx::query(
        r#"
        insert into public.govai_hosted_api_keys
          (team_id, ledger_tenant_id, key_hash, key_prefix, created_by_user_id)
        values ($1, $2, $3, $4, $5)
        "#,
    )
    .bind(team_id)
    .bind(&ledger_tenant_id)
    .bind(&key_hash)
    .bind(&key_prefix)
    .bind(user_id)
    .execute(pool)
    .await
    .map_err(|e| format!("insert hosted api key: {e}"))?;

    sqlx::query(
        r#"
        insert into public.govai_team_onboarding (team_id, current_step, api_key_issued_at, ledger_bound_at, updated_at)
        values ($1, 'api_key_issued', now(), now(), now())
        on conflict (team_id) do update set
          current_step = 'api_key_issued',
          api_key_issued_at = coalesce(public.govai_team_onboarding.api_key_issued_at, excluded.api_key_issued_at),
          ledger_bound_at = coalesce(public.govai_team_onboarding.ledger_bound_at, excluded.ledger_bound_at),
          updated_at = now()
        "#,
    )
    .bind(team_id)
    .execute(pool)
    .await
    .map_err(|e| format!("upsert onboarding: {e}"))?;

    product_ops::upsert_team_ledger_binding(pool, team_id, &ledger_tenant_id)
        .await
        .map_err(|e| format!("ledger binding: {e}"))?;

    sqlx::query(
        r#"
        insert into public.govai_api_key_billing (key_hash, team_id)
        values ($1, $2)
        on conflict (key_hash) do update set team_id = excluded.team_id
        "#,
    )
    .bind(&key_hash)
    .bind(team_id)
    .execute(pool)
    .await
    .map_err(|e| format!("api key billing map: {e}"))?;

    sqlx::query(
        r#"
        insert into public.tenant_billing_accounts (tenant_id, subscription_status)
        values ($1, 'none')
        on conflict (tenant_id) do nothing
        "#,
    )
    .bind(&ledger_tenant_id)
    .execute(pool)
    .await
    .map_err(|e| format!("billing placeholder: {e}"))?;

    audit_api_key::register_hosted_key_hash(&key_hash, &ledger_tenant_id);

    Ok(ProvisionResult {
        team_id,
        ledger_tenant_id,
        api_key,
        key_prefix,
        reused_existing: false,
    })
}

struct ActiveKeyRow {
    key_prefix: String,
}

async fn active_hosted_key_for_team(
    pool: &DbPool,
    team_id: Uuid,
) -> Result<Option<ActiveKeyRow>, sqlx::Error> {
    let row = sqlx::query(
        r#"
        select key_prefix
        from public.govai_hosted_api_keys
        where team_id = $1 and revoked_at is null
        limit 1
        "#,
    )
    .bind(team_id)
    .fetch_optional(pool)
    .await?;

    Ok(row.map(|r| ActiveKeyRow {
        key_prefix: r.get("key_prefix"),
    }))
}

#[derive(Debug, serde::Serialize)]
pub struct OnboardingStatus {
    pub team_id: String,
    pub stage: String,
    pub ledger_tenant_id: Option<String>,
    pub api_key_issued: bool,
    pub api_key_prefix: Option<String>,
    pub ledger_bound: bool,
    pub billing_checkout_started: bool,
    pub first_evidence_recorded: bool,
}

pub async fn onboarding_status(
    pool: &DbPool,
    team_id: Uuid,
) -> Result<OnboardingStatus, sqlx::Error> {
    let onboarding = sqlx::query(
        r#"
        select current_step, api_key_issued_at, ledger_bound_at, billing_checkout_at, first_evidence_at
        from public.govai_team_onboarding
        where team_id = $1
        "#,
    )
    .bind(team_id)
    .fetch_optional(pool)
    .await?;

    let key_row = sqlx::query(
        r#"
        select key_prefix, ledger_tenant_id
        from public.govai_hosted_api_keys
        where team_id = $1 and revoked_at is null
        limit 1
        "#,
    )
    .bind(team_id)
    .fetch_optional(pool)
    .await?;

    let ledger_binding = product_ops::get_ledger_tenant_for_team(pool, team_id)
        .await
        .ok()
        .flatten();

    let stage = onboarding
        .as_ref()
        .map(|r| r.get::<String, _>("current_step"))
        .unwrap_or_else(|| "not_started".to_string());

    Ok(OnboardingStatus {
        team_id: team_id.to_string(),
        stage,
        ledger_tenant_id: key_row
            .as_ref()
            .map(|r| r.get::<String, _>("ledger_tenant_id"))
            .or_else(|| ledger_binding.clone()),
        api_key_issued: key_row.is_some(),
        api_key_prefix: key_row.map(|r| r.get("key_prefix")),
        ledger_bound: ledger_binding.is_some(),
        billing_checkout_started: onboarding
            .as_ref()
            .and_then(|r| {
                r.try_get::<Option<chrono::DateTime<chrono::Utc>>, _>("billing_checkout_at")
                    .ok()
            })
            .flatten()
            .is_some(),
        first_evidence_recorded: onboarding
            .as_ref()
            .and_then(|r| {
                r.try_get::<Option<chrono::DateTime<chrono::Utc>>, _>("first_evidence_at")
                    .ok()
            })
            .flatten()
            .is_some(),
    })
}

pub async fn mark_billing_checkout_started(
    pool: &DbPool,
    team_id: Uuid,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        insert into public.govai_team_onboarding (team_id, current_step, billing_checkout_at, updated_at)
        values ($1, 'billing_checkout', now(), now())
        on conflict (team_id) do update set
          current_step = 'billing_checkout',
          billing_checkout_at = coalesce(public.govai_team_onboarding.billing_checkout_at, now()),
          updated_at = now()
        "#,
    )
    .bind(team_id)
    .execute(pool)
    .await?;
    Ok(())
}
