//! Per-API-key request counts for rate limiting (monetization / quotas).
//! `request_count` is the legacy total; `evidence_ingest_count` and `compliance_summary_read_count`
//! split the two operations that previously only incremented `request_count`.

use crate::db::DbPool;
use sha2::{Digest, Sha256};
use sqlx::Row;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Operational usage channel (not billing; billing is `metering` on `POST /evidence`).
#[derive(Debug, Clone, Copy)]
pub enum UsageChannel {
    /// Successful `POST /evidence` after auth.
    EvidenceIngest,
    /// `GET /compliance-summary` (tracked separately from headline metering).
    ComplianceSummaryRead,
}

#[derive(Debug, Clone, Default)]
struct ChannelUsage {
    /// Legacy: total tracked requests (should track ev + comp after migration; kept +=1 each op).
    request: u64,
    evidence: u64,
    compliance: u64,
}

#[derive(Debug, Clone)]
pub enum UsageError {
    /// Configured quota exceeded.
    QuotaExceeded {
        limit: u64,
        current: u64,
    },
    Database(String),
}

/// Stable id for a bearer token; used as map key and in Postgres.
pub fn key_fingerprint(token: &str) -> String {
    let mut h = Sha256::new();
    h.update(token.as_bytes());
    hex::encode(h.finalize())
}

#[derive(Clone)]
pub struct ApiUsageState {
    inner: Arc<ApiUsageInner>,
}

enum ApiUsageInner {
    Memory(Mutex<HashMap<String, ChannelUsage>>),
    Postgres { pool: DbPool },
}

impl ApiUsageState {
    /// `GOVAI_API_USAGE_STORE`: `memory` (default) or `postgres`.
    pub fn from_env(pool: &DbPool) -> Result<Self, String> {
        let mode = std::env::var("GOVAI_API_USAGE_STORE")
            .map(|s| s.trim().to_lowercase())
            .unwrap_or_else(|_| "memory".to_string());
        if mode.is_empty() || mode == "memory" {
            return Ok(Self {
                inner: Arc::new(ApiUsageInner::Memory(Mutex::new(HashMap::new()))),
            });
        }
        if mode == "postgres" {
            return Ok(Self {
                inner: Arc::new(ApiUsageInner::Postgres { pool: pool.clone() }),
            });
        }
        Err(format!(
            "GOVAI_API_USAGE_STORE must be 'memory' or 'postgres', got '{}'",
            mode
        ))
    }

    /// Increments usage for the given channel. Legacy `max_requests` applies to the **total** `request_count` only.
    /// When `max_requests` is `None`, the counter is incremented and never rejected.
    pub async fn try_increment(
        &self,
        token: &str,
        max_requests: Option<u64>,
        channel: UsageChannel,
    ) -> Result<(), UsageError> {
        let fp = key_fingerprint(token);
        match &*self.inner {
            ApiUsageInner::Memory(m) => {
                let mut g = m.lock().map_err(|e| UsageError::Database(e.to_string()))?;
                let c = g.entry(fp).or_default();
                if let Some(lim) = max_requests {
                    if c.request >= lim {
                        return Err(UsageError::QuotaExceeded {
                            limit: lim,
                            current: c.request,
                        });
                    }
                }
                c.request += 1;
                match channel {
                    UsageChannel::EvidenceIngest => c.evidence += 1,
                    UsageChannel::ComplianceSummaryRead => c.compliance += 1,
                }
                Ok(())
            }
            ApiUsageInner::Postgres { pool } => {
                try_increment_postgres(pool, &fp, max_requests, channel).await
            }
        }
    }
}

async fn try_increment_postgres(
    pool: &DbPool,
    key_hash: &str,
    max_requests: Option<u64>,
    channel: UsageChannel,
) -> Result<(), UsageError> {
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| UsageError::Database(e.to_string()))?;

    let row = sqlx::query(
        r#"
        select request_count, coalesce(evidence_ingest_count, 0) as e, coalesce(compliance_summary_read_count, 0) as c
        from public.govai_api_key_usage
        where key_hash = $1
        for update
        "#,
    )
    .bind(key_hash)
    .fetch_optional(&mut *tx)
    .await
    .map_err(|e| UsageError::Database(e.to_string()))?;

    let current: i64 = match &row {
        None => 0,
        Some(r) => r.get(0),
    };

    if let Some(lim) = max_requests {
        let c = current as u64;
        if c >= lim {
            tx.rollback()
                .await
                .map_err(|e| UsageError::Database(e.to_string()))?;
            return Err(UsageError::QuotaExceeded {
                limit: lim,
                current: c,
            });
        }
    }

    let (set_ev, set_comp) = match channel {
        UsageChannel::EvidenceIngest => (1i64, 0i64),
        UsageChannel::ComplianceSummaryRead => (0i64, 1i64),
    };

    if row.is_none() {
        sqlx::query(
            r#"
            insert into public.govai_api_key_usage
              (key_hash, request_count, evidence_ingest_count, compliance_summary_read_count)
            values ($1, 1, $2, $3)
            "#,
        )
        .bind(key_hash)
        .bind(set_ev)
        .bind(set_comp)
        .execute(&mut *tx)
        .await
        .map_err(|e| UsageError::Database(e.to_string()))?;
    } else {
        sqlx::query(
            r#"
            update public.govai_api_key_usage
            set
              request_count = request_count + 1,
              evidence_ingest_count = evidence_ingest_count + $2,
              compliance_summary_read_count = compliance_summary_read_count + $3
            where key_hash = $1
            "#,
        )
        .bind(key_hash)
        .bind(set_ev)
        .bind(set_comp)
        .execute(&mut *tx)
        .await
        .map_err(|e| UsageError::Database(e.to_string()))?;
    }

    tx.commit()
        .await
        .map_err(|e| UsageError::Database(e.to_string()))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn key_fingerprint_stable() {
        let a = key_fingerprint("secret1");
        assert_eq!(a, key_fingerprint("secret1"));
        assert_ne!(a, key_fingerprint("secret2"));
    }
}
