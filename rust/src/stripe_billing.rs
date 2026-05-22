//! Ledger-tenant Stripe billing: checkout sessions, webhook-driven account rows, metered usage reports, enforcement gate.

use crate::audit_api_key;
use crate::billing_trace;
use crate::db::DbPool;
use crate::govai_environment::GovaiEnvironment;
use axum::http::HeaderMap;
use chrono::{DateTime, Datelike, TimeZone, Utc};
use serde_json::{json, Value};
use sqlx::Row;

const ACTIVE_STATUSES: &[&str] = &["active", "trialing"];

pub const BILLING_UNIT_EVIDENCE_EVENT: &str = "evidence_event";
pub const BILLING_UNIT_COMPLIANCE_CHECK: &str = "compliance_check";
pub const BILLING_UNIT_AUDIT_EXPORT: &str = "audit_export";
pub const BILLING_UNIT_DISCOVERY_SCAN: &str = "discovery_scan";

pub static ALL_BILLING_UNITS: &[&str] = &[
    BILLING_UNIT_EVIDENCE_EVENT,
    BILLING_UNIT_COMPLIANCE_CHECK,
    BILLING_UNIT_AUDIT_EXPORT,
    BILLING_UNIT_DISCOVERY_SCAN,
];

pub fn ledger_tenant_for_billing_headers(
    headers: &HeaderMap,
    deployment_env: GovaiEnvironment,
) -> Result<String, String> {
    audit_api_key::require_tenant_id_from_api_key_for_ledger(headers, deployment_env)
}

/// Billing tenant scope including DB-issued API keys.
pub async fn ledger_tenant_for_billing_headers_async(
    pool: &DbPool,
    headers: &HeaderMap,
    deployment_env: GovaiEnvironment,
) -> Result<String, String> {
    crate::tenant_api_keys::resolve_ledger_tenant_for_bearer(pool, headers, deployment_env).await
}

fn enc_val(s: &str) -> String {
    urlencoding::encode(s).into_owned()
}

pub fn billing_enforcement_enabled() -> bool {
    matches!(
        std::env::var("GOVAI_BILLING_ENFORCEMENT")
            .map(|s| s.trim().to_ascii_lowercase())
            .unwrap_or_default()
            .as_str(),
        "1" | "true" | "yes" | "on"
    )
}

/// Paths that remain reachable without an active/trialing subscription when enforcement is on.
pub fn billing_enforcement_exempt_path(path: &str) -> bool {
    matches!(
        path,
        "/billing/checkout-session"
            | "/billing/status"
            | "/billing/portal-session"
            | "/billing/invoices"
            | "/billing/reconciliation"
            | "/stripe/webhook"
    )
}

pub fn stripe_secret_key() -> Result<String, String> {
    let s = std::env::var("GOVAI_STRIPE_SECRET_KEY")
        .map_err(|_| "GOVAI_STRIPE_SECRET_KEY is not set".to_string())?;
    let t = s.trim();
    if t.is_empty() {
        return Err("GOVAI_STRIPE_SECRET_KEY is empty".into());
    }
    Ok(t.to_string())
}

pub fn subscription_status_is_active(status: &str) -> bool {
    ACTIVE_STATUSES.contains(&status.to_ascii_lowercase().as_str())
}

/// Returns true if tenant may use billable hosted APIs (active or trialing subscription row).
pub async fn tenant_subscription_gate(pool: &DbPool, tenant_id: &str) -> Result<bool, sqlx::Error> {
    let row: Option<(String,)> = sqlx::query_as(
        r#"
        select subscription_status
        from public.tenant_billing_accounts
        where tenant_id = $1
        "#,
    )
    .bind(tenant_id)
    .fetch_optional(pool)
    .await?;
    let Some((status,)) = row else {
        return Ok(false);
    };
    Ok(subscription_status_is_active(status.as_str()))
}

fn jstr(v: &Value, path: &[&str]) -> Option<String> {
    let mut cur = v;
    for p in path {
        cur = cur.get(*p)?;
    }
    cur.as_str().map(|s| s.to_string())
}

fn jstr_opt(v: &Value, path: &[&str]) -> Option<String> {
    jstr(v, path).filter(|s| !s.is_empty())
}

fn unix_ts_to_utc(ts: i64) -> DateTime<Utc> {
    Utc.timestamp_opt(ts, 0).single().unwrap_or_else(Utc::now)
}

/// Upsert tenant billing row by tenant_id (primary key).
pub async fn upsert_tenant_billing_account(
    pool: &DbPool,
    tenant_id: &str,
    stripe_customer_id: Option<&str>,
    stripe_subscription_id: Option<&str>,
    stripe_subscription_item_id: Option<&str>,
    subscription_status: &str,
    current_period_start: Option<DateTime<Utc>>,
    current_period_end: Option<DateTime<Utc>>,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        insert into public.tenant_billing_accounts (
          tenant_id, stripe_customer_id, stripe_subscription_id, stripe_subscription_item_id,
          subscription_status, current_period_start, current_period_end, updated_at
        )
        values ($1, $2, $3, $4, $5, $6, $7, now())
        on conflict (tenant_id) do update set
          stripe_customer_id = coalesce(excluded.stripe_customer_id, public.tenant_billing_accounts.stripe_customer_id),
          stripe_subscription_id = coalesce(excluded.stripe_subscription_id, public.tenant_billing_accounts.stripe_subscription_id),
          stripe_subscription_item_id = coalesce(excluded.stripe_subscription_item_id, public.tenant_billing_accounts.stripe_subscription_item_id),
          subscription_status = excluded.subscription_status,
          current_period_start = coalesce(excluded.current_period_start, public.tenant_billing_accounts.current_period_start),
          current_period_end = coalesce(excluded.current_period_end, public.tenant_billing_accounts.current_period_end),
          updated_at = now()
        "#,
    )
    .bind(tenant_id)
    .bind(stripe_customer_id)
    .bind(stripe_subscription_id)
    .bind(stripe_subscription_item_id)
    .bind(subscription_status)
    .bind(current_period_start)
    .bind(current_period_end)
    .execute(pool)
    .await?;
    Ok(())
}

async fn find_tenant_by_stripe_customer(
    pool: &DbPool,
    customer_id: &str,
) -> Result<Option<String>, sqlx::Error> {
    let r: Option<(String,)> = sqlx::query_as(
        r#"select tenant_id from public.tenant_billing_accounts where stripe_customer_id = $1 limit 1"#,
    )
    .bind(customer_id)
    .fetch_optional(pool)
    .await?;
    Ok(r.map(|t| t.0))
}

fn first_subscription_item_id(sub: &Value) -> Option<String> {
    sub.get("items")?
        .get("data")?
        .as_array()?
        .first()?
        .get("id")?
        .as_str()
        .map(|s| s.to_string())
}

fn env_price_for_unit(unit: &str) -> Option<String> {
    let key = match unit {
        BILLING_UNIT_EVIDENCE_EVENT => "GOVAI_STRIPE_PRICE_EVIDENCE_EVENT",
        BILLING_UNIT_COMPLIANCE_CHECK => "GOVAI_STRIPE_PRICE_COMPLIANCE_CHECK",
        BILLING_UNIT_AUDIT_EXPORT => "GOVAI_STRIPE_PRICE_AUDIT_EXPORT",
        BILLING_UNIT_DISCOVERY_SCAN => "GOVAI_STRIPE_PRICE_DISCOVERY_SCAN",
        _ => return None,
    };
    std::env::var(key)
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
}

pub fn billing_unit_for_stripe_price_id(price_id: &str) -> Option<&'static str> {
    let pid = price_id.trim();
    for u in ALL_BILLING_UNITS {
        if env_price_for_unit(u).as_deref() == Some(pid) {
            return Some(u);
        }
    }
    if let Ok(legacy) = std::env::var("GOVAI_STRIPE_PRICE_ID") {
        if legacy.trim() == pid {
            return Some(BILLING_UNIT_EVIDENCE_EVENT);
        }
    }
    None
}

pub fn log_stripe_unknown_price_warning(
    tenant_id: &str,
    subscription_id: &str,
    price_id: &str,
    item_id: &str,
) {
    let line = json!({
        "level": "WARN",
        "msg": "stripe_subscription_item_unknown_price",
        "tenant_id": tenant_id,
        "stripe_subscription_id": subscription_id,
        "stripe_price_id": price_id,
        "stripe_subscription_item_id": item_id,
    });
    eprintln!("{}", line);
}

fn price_id_from_item(item: &Value) -> Option<String> {
    item.get("price")?
        .get("id")?
        .as_str()
        .map(|s| s.to_string())
        .filter(|s| !s.is_empty())
}

pub async fn sync_subscription_items_from_subscription_json(
    pool: &DbPool,
    tenant_id: &str,
    subscription: &Value,
) -> Result<(), String> {
    let sub_id =
        jstr(subscription, &["id"]).ok_or_else(|| "subscription missing id".to_string())?;
    let data = subscription
        .pointer("/items/data")
        .and_then(|x| x.as_array())
        .cloned()
        .unwrap_or_default();
    for item in &data {
        let item_id = jstr(item, &["id"]).unwrap_or_default();
        if item_id.is_empty() {
            continue;
        }
        let price_id = price_id_from_item(item).unwrap_or_default();
        if price_id.is_empty() {
            continue;
        }
        let Some(unit) = billing_unit_for_stripe_price_id(&price_id) else {
            log_stripe_unknown_price_warning(tenant_id, &sub_id, &price_id, &item_id);
            continue;
        };
        sqlx::query(
            r#"
            insert into public.tenant_billing_subscription_items (
              tenant_id, billing_unit, stripe_subscription_id, stripe_subscription_item_id,
              stripe_price_id, active, updated_at
            )
            values ($1, $2, $3, $4, $5, true, now())
            on conflict (tenant_id, billing_unit) do update set
              stripe_subscription_id = excluded.stripe_subscription_id,
              stripe_subscription_item_id = excluded.stripe_subscription_item_id,
              stripe_price_id = excluded.stripe_price_id,
              active = true,
              updated_at = now()
            "#,
        )
        .bind(tenant_id)
        .bind(unit)
        .bind(&sub_id)
        .bind(&item_id)
        .bind(&price_id)
        .execute(pool)
        .await
        .map_err(|e| e.to_string())?;
    }
    Ok(())
}

pub async fn record_usage_attribution(
    pool: &DbPool,
    tenant_id: &str,
    billing_unit: &str,
    run_id: &str,
    verdict: Option<&str>,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        insert into public.tenant_billing_usage_attributions (tenant_id, billing_unit, run_id, occurred_at, verdict)
        values ($1, $2, $3, now(), $4)
        "#,
    )
    .bind(tenant_id)
    .bind(billing_unit)
    .bind(run_id)
    .bind(verdict)
    .execute(pool)
    .await?;
    Ok(())
}

async fn resolve_tenant_from_subscription(
    pool: &DbPool,
    sub: &Value,
) -> Result<Option<String>, sqlx::Error> {
    if let Some(t) = jstr_opt(sub, &["metadata", "tenant_id"]) {
        return Ok(Some(t));
    }
    if let Some(cust) = jstr_opt(sub, &["customer"]) {
        return find_tenant_by_stripe_customer(pool, &cust).await;
    }
    Ok(None)
}

pub async fn process_checkout_session_completed(pool: &DbPool, obj: &Value) -> Result<(), String> {
    let tenant_id = jstr_opt(obj, &["client_reference_id"])
        .or_else(|| jstr_opt(obj, &["metadata", "tenant_id"]))
        .ok_or_else(|| {
            "checkout.session.completed: missing client_reference_id and metadata.tenant_id"
                .to_string()
        })?;
    let customer = jstr_opt(obj, &["customer"]);
    let subscription = jstr_opt(obj, &["subscription"]);
    upsert_tenant_billing_account(
        pool,
        &tenant_id,
        customer.as_deref(),
        subscription.as_deref(),
        None,
        if subscription.is_some() {
            "incomplete"
        } else {
            "none"
        },
        None,
        None,
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn process_subscription_object(
    pool: &DbPool,
    sub: &Value,
    deleted: bool,
) -> Result<(), String> {
    let Some(tenant_id) = resolve_tenant_from_subscription(pool, sub)
        .await
        .map_err(|e| e.to_string())?
    else {
        return Ok(());
    };
    let customer = jstr_opt(sub, &["customer"]);
    let sub_id = jstr(sub, &["id"]).ok_or_else(|| "subscription missing id".to_string())?;
    let item_id = first_subscription_item_id(sub);
    if deleted {
        upsert_tenant_billing_account(
            pool,
            &tenant_id,
            customer.as_deref(),
            Some(&sub_id),
            item_id.as_deref(),
            "canceled",
            None,
            None,
        )
        .await
        .map_err(|e| e.to_string())?;
        return Ok(());
    }
    let status = jstr(sub, &["status"]).unwrap_or_else(|| "none".into());
    let cps = sub
        .get("current_period_start")
        .and_then(Value::as_i64)
        .map(unix_ts_to_utc);
    let cpe = sub
        .get("current_period_end")
        .and_then(Value::as_i64)
        .map(unix_ts_to_utc);
    upsert_tenant_billing_account(
        pool,
        &tenant_id,
        customer.as_deref(),
        Some(&sub_id),
        item_id.as_deref(),
        &status,
        cps,
        cpe,
    )
    .await
    .map_err(|e| e.to_string())?;
    sync_subscription_items_from_subscription_json(pool, &tenant_id, sub).await?;
    if status == "active" || status == "trialing" {
        let _ = crate::product_ops::try_record_first_milestone(
            pool,
            &tenant_id,
            "first_subscription_activation",
            None,
            serde_json::json!({ "stripe_status": status, "subscription_id": sub_id }),
        )
        .await;
        let _ = crate::product_ops::recompute_tenant_health(pool, &tenant_id).await;
    }
    Ok(())
}

pub async fn process_invoice(pool: &DbPool, inv: &Value, paid: bool) -> Result<(), String> {
    let Some(customer_id) = jstr_opt(inv, &["customer"]) else {
        return Ok(());
    };
    let Some(tenant_id) = find_tenant_by_stripe_customer(pool, &customer_id)
        .await
        .map_err(|e| e.to_string())?
    else {
        // No GovAI tenant mapped to this Stripe customer yet — not an error for the webhook.
        return Ok(());
    };
    let inv_status = if paid { "paid" } else { "failed" };
    sqlx::query(
        r#"
        update public.tenant_billing_accounts
        set billing_invoice_status = $2,
            subscription_status = case when $3 = true then subscription_status else 'past_due' end,
            updated_at = now()
        where tenant_id = $1
        "#,
    )
    .bind(&tenant_id)
    .bind(inv_status)
    .bind(paid)
    .execute(pool)
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

/// Side effects after a verified Stripe event is first persisted (idempotent at event id level).
pub async fn process_stripe_webhook(pool: &DbPool, event: &Value) -> Result<(), String> {
    let typ = jstr(event, &["type"]).ok_or_else(|| "missing type".to_string())?;
    let obj = event
        .get("data")
        .and_then(|d| d.get("object"))
        .ok_or_else(|| "missing data.object".to_string())?;
    match typ.as_str() {
        "checkout.session.completed" => process_checkout_session_completed(pool, obj).await,
        "customer.subscription.created" | "customer.subscription.updated" => {
            process_subscription_object(pool, obj, false).await
        }
        "customer.subscription.deleted" => process_subscription_object(pool, obj, true).await,
        "invoice.paid" | "invoice.payment_succeeded" => process_invoice(pool, obj, true).await,
        "invoice.payment_failed" => process_invoice(pool, obj, false).await,
        _ => Ok(()),
    }
}

/// Stripe Price id for self-serve Pro checkout (`GOVAI_STRIPE_PRICE_PRO`, legacy `GOVAI_STRIPE_PRICE_TEAM`).
pub fn default_pro_checkout_price_id() -> Result<String, String> {
    for key in ["GOVAI_STRIPE_PRICE_PRO", "GOVAI_STRIPE_PRICE_TEAM"] {
        if let Ok(v) = std::env::var(key) {
            let t = v.trim();
            if t.starts_with("price_") {
                return Ok(t.to_string());
            }
        }
    }
    Err(
        "Set GOVAI_STRIPE_PRICE_PRO (or legacy GOVAI_STRIPE_PRICE_TEAM) to a Stripe Price id (price_…)"
            .into(),
    )
}

fn env_price_id(key: &str) -> Option<String> {
    std::env::var(key)
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| s.starts_with("price_"))
}

/// Map Stripe subscription line items to a commercial plan id when price env vars are set.
pub fn commercial_plan_from_billing_units(units: &[BillingUnitRowJson]) -> Option<String> {
    let enterprise_price = env_price_id("GOVAI_STRIPE_PRICE_ENTERPRISE");
    if units.iter().any(|u| {
        enterprise_price
            .as_ref()
            .is_some_and(|p| p == &u.stripe_price_id)
    }) {
        return Some("enterprise".to_string());
    }
    let pro_prices: Vec<String> = ["GOVAI_STRIPE_PRICE_PRO", "GOVAI_STRIPE_PRICE_TEAM"]
        .iter()
        .filter_map(|k| env_price_id(k))
        .collect();
    if units.iter().any(|u| pro_prices.iter().any(|p| p == &u.stripe_price_id)) {
        return Some("pro".to_string());
    }
    None
}

/// Resolve commercial plan id (`free` | `pro` | `enterprise`) from billing row + subscription items.
///
/// Entitlement to call hosted APIs is separate (`can_use_hosted_api`); past-due tenants may still
/// display Pro while API access is blocked.
pub fn commercial_plan_from_status(status: &TenantBillingStatusJson) -> String {
    if let Some(plan) = commercial_plan_from_billing_units(&status.billing_units) {
        return plan;
    }
    let sub = status.subscription_status.to_ascii_lowercase();
    if subscription_status_is_active(sub.as_str()) {
        return "pro".to_string();
    }
    if status.stripe_subscription_id.is_some() {
        match sub.as_str() {
            "past_due" | "unpaid" | "incomplete" => return "pro".to_string(),
            _ => {}
        }
    }
    "free".to_string()
}

pub async fn commercial_plan_for_tenant(
    pool: &DbPool,
    tenant_id: &str,
) -> Result<String, sqlx::Error> {
    let status = billing_status_for_tenant(pool, tenant_id).await?;
    Ok(commercial_plan_from_status(&status))
}

#[derive(Debug, serde::Serialize)]
pub struct BillingUnitRowJson {
    pub billing_unit: String,
    pub stripe_price_id: String,
    pub stripe_subscription_item_id: String,
    pub active: bool,
}

#[derive(Debug, serde::Serialize)]
pub struct TenantBillingStatusJson {
    pub tenant_id: String,
    pub stripe_customer_id: Option<String>,
    pub stripe_subscription_id: Option<String>,
    pub stripe_subscription_item_id: Option<String>,
    pub subscription_status: String,
    pub current_period_start: Option<String>,
    pub current_period_end: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub latest_invoice_status: Option<String>,
    /// Marketing/API plan id: `free`, `pro`, or `enterprise`.
    pub commercial_plan: String,
    pub commercial_plan_display: String,
    /// True when subscription is `active` or `trialing` (hosted API entitlement).
    pub can_use_hosted_api: bool,
    #[serde(default)]
    pub billing_units: Vec<BillingUnitRowJson>,
}

pub async fn billing_status_for_tenant(
    pool: &DbPool,
    tenant_id: &str,
) -> Result<TenantBillingStatusJson, sqlx::Error> {
    let row = sqlx::query(
        r#"
        select stripe_customer_id, stripe_subscription_id, stripe_subscription_item_id,
               subscription_status, current_period_start, current_period_end,
               billing_invoice_status
        from public.tenant_billing_accounts
        where tenant_id = $1
        "#,
    )
    .bind(tenant_id)
    .fetch_optional(pool)
    .await?;
    let Some(r) = row else {
        let commercial_plan = "free".to_string();
        return Ok(TenantBillingStatusJson {
            tenant_id: tenant_id.to_string(),
            stripe_customer_id: None,
            stripe_subscription_id: None,
            stripe_subscription_item_id: None,
            subscription_status: "none".into(),
            current_period_start: None,
            current_period_end: None,
            latest_invoice_status: None,
            commercial_plan: commercial_plan.clone(),
            commercial_plan_display: crate::pricing::commercial_tier_display_name(&commercial_plan)
                .to_string(),
            can_use_hosted_api: false,
            billing_units: Vec::new(),
        });
    };
    let billing_units = sqlx::query(
        r#"
        select billing_unit, stripe_price_id, stripe_subscription_item_id, active
        from public.tenant_billing_subscription_items
        where tenant_id = $1
        order by billing_unit
        "#,
    )
    .bind(tenant_id)
    .fetch_all(pool)
    .await
    .unwrap_or_default()
    .into_iter()
    .filter_map(|row| {
        Some(BillingUnitRowJson {
            billing_unit: row.try_get("billing_unit").ok()?,
            stripe_price_id: row.try_get("stripe_price_id").ok()?,
            stripe_subscription_item_id: row.try_get("stripe_subscription_item_id").ok()?,
            active: row.try_get("active").unwrap_or(true),
        })
    })
    .collect();
    let subscription_status = r
        .try_get::<String, _>("subscription_status")
        .unwrap_or_else(|_| "none".into());
    let latest_invoice_status = r
        .try_get::<Option<String>, _>("billing_invoice_status")
        .ok()
        .flatten();
    let mut status = TenantBillingStatusJson {
        tenant_id: tenant_id.to_string(),
        stripe_customer_id: r
            .try_get::<Option<String>, _>("stripe_customer_id")
            .ok()
            .flatten(),
        stripe_subscription_id: r
            .try_get::<Option<String>, _>("stripe_subscription_id")
            .ok()
            .flatten(),
        stripe_subscription_item_id: r
            .try_get::<Option<String>, _>("stripe_subscription_item_id")
            .ok()
            .flatten(),
        subscription_status: subscription_status.clone(),
        current_period_start: r
            .try_get::<Option<DateTime<Utc>>, _>("current_period_start")
            .ok()
            .flatten()
            .map(|d| d.to_rfc3339()),
        current_period_end: r
            .try_get::<Option<DateTime<Utc>>, _>("current_period_end")
            .ok()
            .flatten()
            .map(|d| d.to_rfc3339()),
        latest_invoice_status,
        commercial_plan: String::new(),
        commercial_plan_display: String::new(),
        can_use_hosted_api: subscription_status_is_active(subscription_status.as_str()),
        billing_units,
    };
    status.commercial_plan = commercial_plan_from_status(&status);
    status.commercial_plan_display =
        crate::pricing::commercial_tier_display_name(&status.commercial_plan).to_string();
    Ok(status)
}

/// Stripe Checkout Session (subscription mode). Returns (session_id, checkout_url).
pub async fn stripe_create_checkout_session(
    secret_key: &str,
    price_id: &str,
    success_url: &str,
    cancel_url: &str,
    tenant_id: &str,
) -> Result<(String, String), String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())?;
    // Keys use Stripe bracket notation; encode values only.
    let body = format!(
        "mode=subscription&success_url={}&cancel_url={}&client_reference_id={}&metadata[tenant_id]={}&subscription_data[metadata][tenant_id]={}&line_items[0][price]={}&line_items[0][quantity]=1",
        enc_val(success_url),
        enc_val(cancel_url),
        enc_val(tenant_id),
        enc_val(tenant_id),
        enc_val(tenant_id),
        enc_val(price_id),
    );
    let resp = client
        .post("https://api.stripe.com/v1/checkout/sessions")
        .basic_auth(secret_key, Some(""))
        .header("Content-Type", "application/x-www-form-urlencoded")
        .body(body)
        .send()
        .await
        .map_err(|e| format!("stripe http: {e}"))?;
    let status = resp.status();
    let text = resp.text().await.map_err(|e| e.to_string())?;
    if !status.is_success() {
        return Err(format!("stripe checkout error {status}: {text}"));
    }
    let v: Value = serde_json::from_str(&text).map_err(|e| format!("stripe json: {e}"))?;
    let id = jstr(&v, &["id"]).ok_or_else(|| format!("stripe response missing id: {text}"))?;
    let url = jstr(&v, &["url"]).ok_or_else(|| format!("stripe response missing url: {text}"))?;
    Ok((id, url))
}

/// POST usage record; returns usage record id from Stripe.
pub async fn stripe_create_usage_record(
    secret_key: &str,
    subscription_item_id: &str,
    quantity: i64,
) -> Result<String, String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())?;
    let body = format!("quantity={}&action=set", enc_val(&quantity.to_string()));
    let url = format!(
        "https://api.stripe.com/v1/subscription_items/{subscription_item_id}/usage_records"
    );
    let resp = client
        .post(&url)
        .basic_auth(secret_key, Some(""))
        .header("Content-Type", "application/x-www-form-urlencoded")
        .body(body)
        .send()
        .await
        .map_err(|e| format!("stripe http: {e}"))?;
    let status = resp.status();
    let text = resp.text().await.map_err(|e| e.to_string())?;
    if !status.is_success() {
        return Err(format!("stripe usage_record error {status}: {text}"));
    }
    let v: Value = serde_json::from_str(&text).map_err(|e| format!("stripe json: {e}"))?;
    jstr(&v, &["id"]).ok_or_else(|| format!("stripe usage_record missing id: {text}"))
}

/// Current billing window: subscription period if known, else UTC calendar month-to-date.
pub async fn resolve_usage_period_for_tenant(
    pool: &DbPool,
    tenant_id: &str,
) -> Result<(DateTime<Utc>, DateTime<Utc>), sqlx::Error> {
    let row = sqlx::query(
        r#"
        select current_period_start, current_period_end
        from public.tenant_billing_accounts
        where tenant_id = $1
        "#,
    )
    .bind(tenant_id)
    .fetch_optional(pool)
    .await?;
    let now = Utc::now();
    if let Some(r) = row {
        let cps: Option<DateTime<Utc>> = r.try_get("current_period_start").ok().flatten();
        let cpe: Option<DateTime<Utc>> = r.try_get("current_period_end").ok().flatten();
        if let (Some(start), Some(end)) = (cps, cpe) {
            if start < end {
                return Ok((start, end));
            }
        }
    }
    let month_start = Utc
        .with_ymd_and_hms(now.year(), now.month(), 1, 0, 0, 0)
        .single()
        .unwrap_or(now);
    Ok((month_start, now))
}

#[derive(Debug, serde::Serialize)]
pub struct ReportUsageOutcome {
    pub idempotent_hit: bool,
    pub report_id: Option<uuid::Uuid>,
    pub quantity: i64,
    pub period_start: String,
    pub period_end: String,
    pub status: String,
    pub stripe_usage_record_id: Option<String>,
}

/// Idempotent usage report + optional Stripe metered push.
pub async fn report_usage_for_tenant(
    pool: &DbPool,
    tenant_id: &str,
    billing_unit: &str,
) -> Result<ReportUsageOutcome, String> {
    let (period_start, period_end) = resolve_usage_period_for_tenant(pool, tenant_id)
        .await
        .map_err(|e| e.to_string())?;
    let qty = billing_trace::count_units_for_tenant(
        pool,
        tenant_id,
        billing_unit,
        period_start,
        period_end,
    )
    .await
    .map_err(|e| e.to_string())?;

    let mut item_id: Option<String> = sqlx::query_scalar(
        r#"
        select stripe_subscription_item_id
        from public.tenant_billing_subscription_items
        where tenant_id = $1 and billing_unit = $2 and active = true
        limit 1
        "#,
    )
    .bind(tenant_id)
    .bind(billing_unit)
    .fetch_optional(pool)
    .await
    .map_err(|e| e.to_string())?
    .flatten();
    if item_id.is_none() && billing_unit == BILLING_UNIT_EVIDENCE_EVENT {
        item_id = sqlx::query_scalar(
            r#"select stripe_subscription_item_id from public.tenant_billing_accounts where tenant_id = $1"#,
        )
        .bind(tenant_id)
        .fetch_optional(pool)
        .await
        .map_err(|e| e.to_string())?
        .flatten();
    }

    let new_report_id: Option<uuid::Uuid> = sqlx::query_scalar(
        r#"
        insert into public.billing_usage_reports
          (tenant_id, billing_unit, quantity, period_start, period_end, stripe_subscription_item_id, status, updated_at)
        values ($1, $2, $3, $4, $5, $6, 'pending', now())
        on conflict (tenant_id, billing_unit, period_start, period_end) do nothing
        returning id
        "#,
    )
    .bind(tenant_id)
    .bind(billing_unit)
    .bind(qty)
    .bind(period_start)
    .bind(period_end)
    .bind(item_id.as_deref())
    .fetch_optional(pool)
    .await
    .map_err(|e| e.to_string())?;

    if new_report_id.is_none() {
        let row = sqlx::query(
            r#"
            select id, status, stripe_usage_record_id, quantity
            from public.billing_usage_reports
            where tenant_id = $1 and billing_unit = $2 and period_start = $3 and period_end = $4
            "#,
        )
        .bind(tenant_id)
        .bind(billing_unit)
        .bind(period_start)
        .bind(period_end)
        .fetch_one(pool)
        .await
        .map_err(|e| e.to_string())?;
        let rid: uuid::Uuid = row
            .try_get::<uuid::Uuid, _>("id")
            .map_err(|e| e.to_string())?;
        let status: String = row.try_get("status").map_err(|e| e.to_string())?;
        let sur: Option<String> = row.try_get("stripe_usage_record_id").unwrap_or(None);
        let stored_qty: i64 = row.try_get("quantity").unwrap_or(qty);
        return Ok(ReportUsageOutcome {
            idempotent_hit: true,
            report_id: Some(rid),
            quantity: stored_qty,
            period_start: period_start.to_rfc3339(),
            period_end: period_end.to_rfc3339(),
            status,
            stripe_usage_record_id: sur,
        });
    }

    let rid = new_report_id.unwrap();

    if let Some(ref sid) = item_id {
        let secret = stripe_secret_key()?;
        match stripe_create_usage_record(&secret, sid, qty).await {
            Ok(usage_id) => {
                sqlx::query(
                    r#"
                    update public.billing_usage_reports
                    set status = 'reported', stripe_usage_record_id = $2, last_error = null, updated_at = now()
                    where id = $1
                    "#,
                )
                .bind(rid)
                .bind(&usage_id)
                .execute(pool)
                .await
                .map_err(|e| e.to_string())?;
                return Ok(ReportUsageOutcome {
                    idempotent_hit: false,
                    report_id: Some(rid),
                    quantity: qty,
                    period_start: period_start.to_rfc3339(),
                    period_end: period_end.to_rfc3339(),
                    status: "reported".into(),
                    stripe_usage_record_id: Some(usage_id),
                });
            }
            Err(e) => {
                sqlx::query(
                    r#"
                    update public.billing_usage_reports
                    set status = 'failed', last_error = $2, updated_at = now()
                    where id = $1
                    "#,
                )
                .bind(rid)
                .bind(&e)
                .execute(pool)
                .await
                .map_err(|e| e.to_string())?;
                return Err(e);
            }
        }
    }

    sqlx::query(
        r#"
        update public.billing_usage_reports
        set status = 'recorded_local', last_error = 'no stripe_subscription_item_id on tenant', updated_at = now()
        where id = $1
        "#,
    )
    .bind(rid)
    .execute(pool)
    .await
    .map_err(|e| e.to_string())?;

    Ok(ReportUsageOutcome {
        idempotent_hit: false,
        report_id: Some(rid),
        quantity: qty,
        period_start: period_start.to_rfc3339(),
        period_end: period_end.to_rfc3339(),
        status: "recorded_local".into(),
        stripe_usage_record_id: None,
    })
}

pub async fn reconciliation_for_tenant(
    pool: &DbPool,
    tenant_id: &str,
    from: DateTime<Utc>,
    to: DateTime<Utc>,
    billing_unit: Option<&str>,
) -> Result<Value, String> {
    let units: Vec<&str> = if let Some(u) = billing_unit.filter(|s| !s.trim().is_empty()) {
        vec![u]
    } else {
        ALL_BILLING_UNITS.to_vec()
    };
    let mut usage = Vec::new();
    for unit in units {
        let runs: Vec<String> = sqlx::query_scalar(
            r#"
            select distinct run_id from public.tenant_billing_usage_attributions
            where tenant_id = $1 and billing_unit = $2 and occurred_at >= $3 and occurred_at < $4
            order by run_id
            "#,
        )
        .bind(tenant_id)
        .bind(unit)
        .bind(from)
        .bind(to)
        .fetch_all(pool)
        .await
        .map_err(|e| e.to_string())?;
        usage.push(json!({
            "billing_unit": unit,
            "runs": runs.into_iter().map(|rid| json!({"run_id": rid})).collect::<Vec<_>>()
        }));
    }
    Ok(json!({
        "ok": true,
        "tenant_id": tenant_id,
        "from": from.to_rfc3339(),
        "to": to.to_rfc3339(),
        "usage": usage
    }))
}

pub async fn stripe_create_billing_portal_session(
    secret_key: &str,
    customer_id: &str,
    return_url: &str,
) -> Result<String, String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())?;
    let body = format!(
        "customer={}&return_url={}",
        enc_val(customer_id),
        enc_val(return_url)
    );
    let resp = client
        .post("https://api.stripe.com/v1/billing_portal/sessions")
        .basic_auth(secret_key, Some(""))
        .header("Content-Type", "application/x-www-form-urlencoded")
        .body(body)
        .send()
        .await
        .map_err(|e| format!("stripe http: {e}"))?;
    let status = resp.status();
    let text = resp.text().await.map_err(|e| e.to_string())?;
    if !status.is_success() {
        return Err(format!("stripe portal error {status}: {text}"));
    }
    let v: Value = serde_json::from_str(&text).map_err(|e| format!("stripe json: {e}"))?;
    jstr(&v, &["url"]).ok_or_else(|| format!("stripe portal missing url: {text}"))
}

pub async fn stripe_list_invoices(
    secret_key: &str,
    customer_id: &str,
    limit: u32,
) -> Result<Vec<Value>, String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())?;
    let url = format!(
        "https://api.stripe.com/v1/invoices?customer={}&limit={}",
        enc_val(customer_id),
        limit
    );
    let resp = client
        .get(url)
        .basic_auth(secret_key, Some(""))
        .send()
        .await
        .map_err(|e| format!("stripe http: {e}"))?;
    let status = resp.status();
    let text = resp.text().await.map_err(|e| e.to_string())?;
    if !status.is_success() {
        return Err(format!("stripe invoices error {status}: {text}"));
    }
    let v: Value = serde_json::from_str(&text).map_err(|e| format!("stripe json: {e}"))?;
    Ok(v.get("data")
        .and_then(|d| d.as_array())
        .cloned()
        .unwrap_or_default())
}
