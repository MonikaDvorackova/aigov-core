//! Self-service onboarding: organization tenant provisioning, billing placeholder, progress.

use crate::db::DbPool;
use crate::product_ops;
use crate::stripe_billing;
use crate::tenant_api_keys::{self, IssuedKeyRow};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sqlx::Row;
use uuid::Uuid;

pub const STEP_ORGANIZATION: &str = "organization";
pub const STEP_BILLING: &str = "billing";
pub const STEP_API_KEY: &str = "api_key";
pub const STEP_CI_CONNECT: &str = "ci_connect";
pub const STEP_FIRST_EVIDENCE: &str = "first_evidence";
pub const STEP_VERDICT: &str = "verdict";
pub const STEP_EXPORT: &str = "export";
pub const STEP_COMPLETE: &str = "complete";

pub const ORDERED_STEPS: &[&str] = &[
    STEP_ORGANIZATION,
    STEP_BILLING,
    STEP_API_KEY,
    STEP_CI_CONNECT,
    STEP_FIRST_EVIDENCE,
    STEP_VERDICT,
    STEP_EXPORT,
    STEP_COMPLETE,
];

#[derive(Debug, Clone, Serialize)]
pub struct OnboardingStatus {
    pub team_id: String,
    pub current_step: String,
    pub completed_steps: Vec<String>,
    pub organization_name: Option<String>,
    pub ledger_tenant_id: Option<String>,
    pub billing_placeholder: bool,
    pub subscription_status: Option<String>,
    pub has_active_api_key: bool,
    pub api_key_prefix: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ProvisionResult {
    pub team_id: String,
    pub organization_name: String,
    pub ledger_tenant_id: String,
    pub onboarding: OnboardingStatus,
}

pub fn ledger_tenant_id_for_team(team_id: Uuid) -> String {
    format!("org-{}", team_id.as_simple())
}

pub async fn get_onboarding_status(
    pool: &DbPool,
    team_id: Uuid,
) -> Result<Option<OnboardingStatus>, sqlx::Error> {
    let row = sqlx::query(
        r#"
        select current_step, completed_steps, organization_name, ledger_tenant_id,
               billing_placeholder_at, primary_api_key_id
        from public.govai_team_onboarding
        where team_id = $1
        "#,
    )
    .bind(team_id)
    .fetch_optional(pool)
    .await?;

    let Some(r) = row else {
        return Ok(None);
    };

    let completed: Vec<String> = r
        .try_get::<Value, _>("completed_steps")
        .ok()
        .and_then(|v| serde_json::from_value(v).ok())
        .unwrap_or_default();
    let ledger_tid: Option<String> = r.try_get("ledger_tenant_id").ok();
    let sub_status = if let Some(ref tid) = ledger_tid {
        billing_status_for_tenant(pool, tid).await.ok().flatten()
    } else {
        None
    };
    let keys = tenant_api_keys::list_active_keys_for_team(pool, team_id)
        .await
        .unwrap_or_default();
    let key_prefix = keys.first().map(|k| k.key_prefix.clone());

    Ok(Some(OnboardingStatus {
        team_id: team_id.to_string(),
        current_step: r.get("current_step"),
        completed_steps: completed,
        organization_name: r.try_get("organization_name").ok(),
        ledger_tenant_id: ledger_tid,
        billing_placeholder: r
            .try_get::<Option<DateTime<Utc>>, _>("billing_placeholder_at")
            .ok()
            .flatten()
            .is_some(),
        subscription_status: sub_status,
        has_active_api_key: !keys.is_empty(),
        api_key_prefix: key_prefix,
    }))
}

async fn billing_status_for_tenant(
    pool: &DbPool,
    tenant_id: &str,
) -> Result<Option<String>, sqlx::Error> {
    let row: Option<(String,)> = sqlx::query_as(
        r#"select subscription_status from public.tenant_billing_accounts where tenant_id = $1"#,
    )
    .bind(tenant_id)
    .fetch_optional(pool)
    .await?;
    Ok(row.map(|r| r.0))
}

pub async fn provision_organization(
    pool: &DbPool,
    user_id: Uuid,
    organization_name: &str,
) -> Result<ProvisionResult, sqlx::Error> {
    let org = organization_name.trim();
    let team_id = match crate::db::get_default_team_for_user(pool, user_id).await? {
        Some(t) => {
            sqlx::query(r#"update public.teams set name = $2 where id = $1"#)
                .bind(t)
                .bind(org)
                .execute(pool)
                .await?;
            t
        }
        None => {
            let team_id = Uuid::new_v4();
            let mut tx = pool.begin().await?;
            sqlx::query(r#"insert into public.teams (id, name) values ($1, $2)"#)
                .bind(team_id)
                .bind(org)
                .execute(&mut *tx)
                .await?;
            sqlx::query(
                r#"insert into public.team_members (team_id, user_id, role) values ($1, $2, 'admin')"#,
            )
            .bind(team_id)
            .bind(user_id)
            .execute(&mut *tx)
            .await?;
            tx.commit().await?;
            team_id
        }
    };

    let ledger_tid = ledger_tenant_id_for_team(team_id);

    sqlx::query(
        r#"
        insert into public.govai_organization_tenants (ledger_tenant_id, team_id, organization_name)
        values ($1, $2, $3)
        on conflict (ledger_tenant_id) do update set organization_name = excluded.organization_name
        "#,
    )
    .bind(&ledger_tid)
    .bind(team_id)
    .bind(org)
    .execute(pool)
    .await?;

    product_ops::upsert_team_ledger_binding(pool, team_id, &ledger_tid).await?;

    stripe_billing::upsert_tenant_billing_account(
        pool,
        &ledger_tid,
        None,
        None,
        None,
        "pending_checkout",
        None,
        None,
    )
    .await?;

    sqlx::query(
        r#"
        insert into public.team_billing (team_id, billing_email)
        values ($1, null)
        on conflict (team_id) do nothing
        "#,
    )
    .bind(team_id)
    .execute(pool)
    .await?;

    let completed = json!([STEP_ORGANIZATION]);
    sqlx::query(
        r#"
        insert into public.govai_team_onboarding (
          team_id, current_step, completed_steps, organization_name, ledger_tenant_id,
          billing_placeholder_at, updated_at
        )
        values ($1, $2, $3, $4, $5, now(), now())
        on conflict (team_id) do update set
          current_step = excluded.current_step,
          completed_steps = excluded.completed_steps,
          organization_name = excluded.organization_name,
          ledger_tenant_id = excluded.ledger_tenant_id,
          billing_placeholder_at = coalesce(public.govai_team_onboarding.billing_placeholder_at, excluded.billing_placeholder_at),
          updated_at = now()
        "#,
    )
    .bind(team_id)
    .bind(STEP_BILLING)
    .bind(completed)
    .bind(org)
    .bind(&ledger_tid)
    .execute(pool)
    .await?;

    let onboarding = get_onboarding_status(pool, team_id)
        .await?
        .expect("onboarding row");

    Ok(ProvisionResult {
        team_id: team_id.to_string(),
        organization_name: org.to_string(),
        ledger_tenant_id: ledger_tid,
        onboarding,
    })
}

pub async fn advance_onboarding_step(
    pool: &DbPool,
    team_id: Uuid,
    step: &str,
) -> Result<Option<OnboardingStatus>, sqlx::Error> {
    if !ORDERED_STEPS.contains(&step) {
        return Ok(get_onboarding_status(pool, team_id).await?);
    }
    let idx = ORDERED_STEPS.iter().position(|s| *s == step).unwrap_or(0);
    let next = ORDERED_STEPS.get(idx + 1).copied().unwrap_or(STEP_COMPLETE);

    sqlx::query(
        r#"
        update public.govai_team_onboarding
        set
          completed_steps = (
            select coalesce(jsonb_agg(distinct e), '[]'::jsonb)
            from (
              select jsonb_array_elements_text(completed_steps) as e
              union all select $2::text
            ) sub
          ),
          current_step = $3,
          updated_at = now()
        where team_id = $1
        "#,
    )
    .bind(team_id)
    .bind(step)
    .bind(next)
    .execute(pool)
    .await?;

    get_onboarding_status(pool, team_id).await
}

pub async fn issue_primary_api_key(
    pool: &DbPool,
    team_id: Uuid,
    user_id: Uuid,
) -> Result<Option<(IssuedKeyRow, String)>, sqlx::Error> {
    let ledger: Option<String> = sqlx::query_scalar(
        r#"select ledger_tenant_id from public.govai_team_onboarding where team_id = $1"#,
    )
    .bind(team_id)
    .fetch_optional(pool)
    .await?;

    let Some(ledger_tid) = ledger else {
        return Ok(None);
    };

    let existing = tenant_api_keys::list_active_keys_for_team(pool, team_id).await?;
    if !existing.is_empty() {
        return Ok(None);
    }

    let (row, raw) =
        tenant_api_keys::issue_api_key(pool, team_id, &ledger_tid, user_id, "default").await?;

    sqlx::query(
        r#"
        update public.govai_team_onboarding
        set primary_api_key_id = $2, current_step = $3, updated_at = now()
        where team_id = $1
        "#,
    )
    .bind(team_id)
    .bind(row.id)
    .bind(STEP_CI_CONNECT)
    .execute(pool)
    .await?;

    let _ = advance_onboarding_step(pool, team_id, STEP_API_KEY).await;

    Ok(Some((row, raw)))
}

/// Hosted Professional plan Stripe price (€499 / $499 Pro tier).
pub fn professional_checkout_price_id() -> Option<String> {
    for key in [
        "GOVAI_STRIPE_PRICE_PRO",
        "GOVAI_STRIPE_PRICE_PROFESSIONAL",
        "GOVAI_STRIPE_PRICE_ID",
        "GOVAI_STRIPE_PRICE_TEAM",
        "GOVAI_STRIPE_PRICE_EVIDENCE_EVENT",
    ] {
        if let Ok(v) = std::env::var(key) {
            let t = v.trim();
            if t.starts_with("price_") {
                return Some(t.to_string());
            }
        }
    }
    None
}

#[derive(Debug, Deserialize)]
pub struct OnboardingCheckoutBody {
    pub success_url: String,
    pub cancel_url: String,
    #[serde(default)]
    pub price_id: Option<String>,
}

pub async fn create_onboarding_checkout(
    pool: &DbPool,
    team_id: Uuid,
    body: &OnboardingCheckoutBody,
) -> Result<(String, String, String), String> {
    let ledger: String = sqlx::query_scalar(
        r#"select ledger_tenant_id from public.govai_team_onboarding where team_id = $1"#,
    )
    .bind(team_id)
    .fetch_optional(pool)
    .await
    .map_err(|e| e.to_string())?
    .ok_or_else(|| "onboarding_not_started".to_string())?;

    let price = body
        .price_id
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty() && s.starts_with("price_"))
        .map(str::to_string)
        .or_else(professional_checkout_price_id)
        .ok_or_else(|| {
            "Set GOVAI_STRIPE_PRICE_PRO or GOVAI_STRIPE_PRICE_ID to the Hosted Professional price (price_…)."
                .to_string()
        })?;

    let sk = stripe_billing::stripe_secret_key()?;
    let (session_id, url) = stripe_billing::stripe_create_checkout_session(
        &sk,
        &price,
        body.success_url.trim(),
        body.cancel_url.trim(),
        &ledger,
    )
    .await?;

    let _ = advance_onboarding_step(pool, team_id, STEP_BILLING)
        .await
        .map_err(|e| e.to_string())?;

    Ok((ledger, session_id, url))
}
