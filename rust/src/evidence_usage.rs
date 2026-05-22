//! Canonical evidence-event quota when `GOVAI_METERING=off`: table `govai_usage_counters`
//! (monthly calendar period, per billing tenant from [`crate::project::billing_tenant_id`] —
//! same scope as `GET /usage`).
//!
//! **What is counted:** each **successful** `POST /evidence` append increments
//! `evidence_events_count` by one (duplicates / validation failures do not increment).
//! This is **not** “runs”; run cardinality is only enforced when `GOVAI_METERING=on`
//! ([`crate::metering`]).
//!
//! When `GOVAI_METERING=on`, team plan limits are enforced in [`crate::govai_api::ingest`] via
//! [`crate::metering`] (monthly evidence events, monthly new run_ids, per-run event cap).

use crate::db::DbPool;
use chrono::{Datelike, NaiveDate, Utc};
use sqlx::Row;

pub const FREE_TIER_EVIDENCE_LIMIT: u64 = 1000;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LegacyEvidenceQuotaExceeded {
    pub used: u64,
    pub limit: u64,
    pub period_start: NaiveDate,
}

#[derive(Debug)]
pub enum CheckEvidenceQuotaError {
    Exceeded(LegacyEvidenceQuotaExceeded),
    Database(String),
}

pub fn current_period_start_utc() -> NaiveDate {
    let now = Utc::now().date_naive();
    NaiveDate::from_ymd_opt(now.year(), now.month(), 1).expect("valid month day")
}

/// Returns `Exceeded` when the tenant is already at or over the monthly evidence cap
/// (ingesting another event would exceed the limit).
pub async fn check_evidence_quota(
    pool: &DbPool,
    tenant_id: &str,
) -> Result<(), CheckEvidenceQuotaError> {
    let period = current_period_start_utc();
    let count: Option<i64> = sqlx::query_scalar(
        r#"
        SELECT evidence_events_count
        FROM govai_usage_counters
        WHERE tenant_id = $1 AND period_start = $2
        "#,
    )
    .bind(tenant_id)
    .bind(period)
    .fetch_optional(pool)
    .await
    .map_err(|e| CheckEvidenceQuotaError::Database(e.to_string()))?;

    let n = count.unwrap_or(0).max(0) as u64;
    if n >= FREE_TIER_EVIDENCE_LIMIT {
        return Err(CheckEvidenceQuotaError::Exceeded(
            LegacyEvidenceQuotaExceeded {
                used: n,
                limit: FREE_TIER_EVIDENCE_LIMIT,
                period_start: period,
            },
        ));
    }
    Ok(())
}

pub async fn increment_evidence_usage(pool: &DbPool, tenant_id: &str) -> Result<(), String> {
    let period = current_period_start_utc();
    sqlx::query(
        r#"
        INSERT INTO govai_usage_counters (tenant_id, period_start, evidence_events_count)
        VALUES ($1, $2, 1)
        ON CONFLICT (tenant_id, period_start)
        DO UPDATE SET
            evidence_events_count = govai_usage_counters.evidence_events_count + 1,
            last_updated_at = now()
        "#,
    )
    .bind(tenant_id)
    .bind(period)
    .execute(pool)
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn increment_compliance_check_usage(
    pool: &DbPool,
    tenant_id: &str,
) -> Result<(), String> {
    let period = current_period_start_utc();
    sqlx::query(
        r#"
        INSERT INTO govai_usage_counters (tenant_id, period_start, compliance_checks_count)
        VALUES ($1, $2, 1)
        ON CONFLICT (tenant_id, period_start)
        DO UPDATE SET
            compliance_checks_count = govai_usage_counters.compliance_checks_count + 1,
            last_updated_at = now()
        "#,
    )
    .bind(tenant_id)
    .bind(period)
    .execute(pool)
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn increment_export_usage(pool: &DbPool, tenant_id: &str) -> Result<(), String> {
    let period = current_period_start_utc();
    sqlx::query(
        r#"
        INSERT INTO govai_usage_counters (tenant_id, period_start, exports_count)
        VALUES ($1, $2, 1)
        ON CONFLICT (tenant_id, period_start)
        DO UPDATE SET
            exports_count = govai_usage_counters.exports_count + 1,
            last_updated_at = now()
        "#,
    )
    .bind(tenant_id)
    .bind(period)
    .execute(pool)
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn increment_discovery_scan_usage(pool: &DbPool, tenant_id: &str) -> Result<(), String> {
    let period = current_period_start_utc();
    sqlx::query(
        r#"
        INSERT INTO govai_usage_counters (tenant_id, period_start, discovery_scans_count)
        VALUES ($1, $2, 1)
        ON CONFLICT (tenant_id, period_start)
        DO UPDATE SET
            discovery_scans_count = govai_usage_counters.discovery_scans_count + 1,
            last_updated_at = now()
        "#,
    )
    .bind(tenant_id)
    .bind(period)
    .execute(pool)
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn get_usage_counters(
    pool: &DbPool,
    tenant_id: &str,
) -> Result<(i64, i64, i64, i64, NaiveDate), String> {
    let period = current_period_start_utc();
    let row = sqlx::query(
        r#"
        SELECT
          evidence_events_count,
          COALESCE(compliance_checks_count, 0) as compliance_checks_count,
          COALESCE(exports_count, 0) as exports_count,
          COALESCE(discovery_scans_count, 0) as discovery_scans_count
        FROM govai_usage_counters
        WHERE tenant_id = $1 AND period_start = $2
        "#,
    )
    .bind(tenant_id)
    .bind(period)
    .fetch_optional(pool)
    .await
    .map_err(|e| e.to_string())?;

    match row {
        None => Ok((0, 0, 0, 0, period)),
        Some(r) => {
            let ev: i64 = r.try_get("evidence_events_count").unwrap_or(0);
            let cc: i64 = r.try_get("compliance_checks_count").unwrap_or(0);
            let ex: i64 = r.try_get("exports_count").unwrap_or(0);
            let ds: i64 = r.try_get("discovery_scans_count").unwrap_or(0);
            Ok((ev, cc, ex, ds, period))
        }
    }
}

pub async fn get_evidence_usage(
    pool: &DbPool,
    tenant_id: &str,
) -> Result<(i64, NaiveDate), String> {
    let period = current_period_start_utc();
    let count: Option<i64> = sqlx::query_scalar(
        r#"
        SELECT evidence_events_count
        FROM govai_usage_counters
        WHERE tenant_id = $1 AND period_start = $2
        "#,
    )
    .bind(tenant_id)
    .bind(period)
    .fetch_optional(pool)
    .await
    .map_err(|e| e.to_string())?;
    Ok((count.unwrap_or(0), period))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::db::DbPool;
    use sqlx::postgres::PgPoolOptions;

    async fn pool() -> Option<DbPool> {
        let url = std::env::var("TEST_DATABASE_URL")
            .or_else(|_| std::env::var("DATABASE_URL"))
            .ok()?;
        let pool = PgPoolOptions::new()
            .max_connections(2)
            .connect(&url)
            .await
            .ok()?;
        sqlx::migrate!("./migrations").run(&pool).await.ok()?;
        Some(pool)
    }

    #[tokio::test]
    async fn increment_increments_counter_by_one() {
        let Some(pool) = pool().await else {
            return;
        };
        let tid = format!("ev_usage_{}", uuid::Uuid::new_v4());
        let p = current_period_start_utc();
        sqlx::query("DELETE FROM govai_usage_counters WHERE tenant_id = $1 AND period_start = $2")
            .bind(&tid)
            .bind(p)
            .execute(&pool)
            .await
            .ok();
        increment_evidence_usage(&pool, &tid).await.expect("inc");
        let (c, _) = get_evidence_usage(&pool, &tid).await.expect("get");
        assert_eq!(c, 1);
    }

    #[tokio::test]
    async fn check_fails_at_free_tier_limit() {
        let Some(pool) = pool().await else {
            return;
        };
        let tid = format!("ev_quota_{}", uuid::Uuid::new_v4());
        let p = current_period_start_utc();
        sqlx::query(
            r#"
            INSERT INTO govai_usage_counters (tenant_id, period_start, evidence_events_count)
            VALUES ($1, $2, $3)
            ON CONFLICT (tenant_id, period_start)
            DO UPDATE SET evidence_events_count = EXCLUDED.evidence_events_count
            "#,
        )
        .bind(&tid)
        .bind(p)
        .bind(FREE_TIER_EVIDENCE_LIMIT as i64)
        .execute(&pool)
        .await
        .expect("seed");
        let err = check_evidence_quota(&pool, &tid)
            .await
            .expect_err("at limit");
        match err {
            CheckEvidenceQuotaError::Exceeded(e) => {
                assert_eq!(e.used, FREE_TIER_EVIDENCE_LIMIT);
                assert_eq!(e.limit, FREE_TIER_EVIDENCE_LIMIT);
                assert_eq!(e.period_start, p);
            }
            CheckEvidenceQuotaError::Database(d) => panic!("unexpected db err: {d}"),
        }
    }
}
