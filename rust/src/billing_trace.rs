//! Durable trace rows linking billable usage to `run_id` + ledger tenant + timestamp.

use crate::db::DbPool;
use chrono::{DateTime, Utc};
use serde::Serialize;
use sqlx::Row;

const DEFAULT_UNIT: &str = "evidence_event";

/// Best-effort: never fails the HTTP ingest path; logs on DB error.
pub async fn record_evidence_ingest_unit(pool: &DbPool, ledger_tenant_id: &str, run_id: &str) {
    if let Err(e) = sqlx::query(
        r#"
        insert into public.govai_billing_usage_trace
          (ledger_tenant_id, run_id, billing_unit)
        values ($1, $2, $3)
        "#,
    )
    .bind(ledger_tenant_id)
    .bind(run_id)
    .bind(DEFAULT_UNIT)
    .execute(pool)
    .await
    {
        eprintln!("billing_trace: failed to record usage unit: {e}");
    }
}

#[derive(Serialize)]
pub struct UsageTraceRow {
    pub tenant_id: String,
    pub run_id: String,
    pub occurred_at: DateTime<Utc>,
}

pub struct UsageSummary {
    pub tenant_id: String,
    pub billing_unit: String,
    pub count: i64,
    pub window_start: DateTime<Utc>,
    pub window_end: DateTime<Utc>,
    pub traces: Vec<UsageTraceRow>,
}

pub async fn count_units_for_tenant(
    pool: &DbPool,
    ledger_tenant_id: &str,
    billing_unit: &str,
    window_start: DateTime<Utc>,
    window_end: DateTime<Utc>,
) -> Result<i64, sqlx::Error> {
    sqlx::query_scalar(
        r#"
        select count(*)::bigint
        from public.govai_billing_usage_trace
        where ledger_tenant_id = $1
          and billing_unit = $2
          and created_at >= $3
          and created_at < $4
        "#,
    )
    .bind(ledger_tenant_id)
    .bind(billing_unit)
    .bind(window_start)
    .bind(window_end)
    .fetch_one(pool)
    .await
}

pub async fn usage_summary_for_tenant(
    pool: &DbPool,
    ledger_tenant_id: &str,
    billing_unit: &str,
    window_start: DateTime<Utc>,
    window_end: DateTime<Utc>,
) -> Result<UsageSummary, sqlx::Error> {
    let count: i64 = sqlx::query_scalar(
        r#"
        select count(*)::bigint
        from public.govai_billing_usage_trace
        where ledger_tenant_id = $1
          and billing_unit = $2
          and created_at >= $3
          and created_at < $4
        "#,
    )
    .bind(ledger_tenant_id)
    .bind(billing_unit)
    .bind(window_start)
    .bind(window_end)
    .fetch_one(pool)
    .await?;

    let rows = sqlx::query(
        r#"
        select run_id, created_at
        from public.govai_billing_usage_trace
        where ledger_tenant_id = $1
          and billing_unit = $2
          and created_at >= $3
          and created_at < $4
        order by created_at desc
        limit 500
        "#,
    )
    .bind(ledger_tenant_id)
    .bind(billing_unit)
    .bind(window_start)
    .bind(window_end)
    .fetch_all(pool)
    .await?;

    let traces = rows
        .into_iter()
        .map(|r| UsageTraceRow {
            tenant_id: ledger_tenant_id.to_string(),
            run_id: r.get::<String, _>("run_id"),
            occurred_at: r.get::<DateTime<Utc>, _>("created_at"),
        })
        .collect();

    Ok(UsageSummary {
        tenant_id: ledger_tenant_id.to_string(),
        billing_unit: billing_unit.to_string(),
        count,
        window_start,
        window_end,
        traces,
    })
}
