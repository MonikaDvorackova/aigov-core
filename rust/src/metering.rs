//! Team-scoped metering when `GOVAI_METERING=on`. Plan limits are code constants; default plan from `GOVAI_DEFAULT_PLAN`.
//!
//! **What is counted (billable / limit-relevant):**
//! - **Evidence events:** each successful `POST /evidence` append for the API key’s team increments
//!   monthly `evidence_events` and updates per-run `event_count` (same team as `GET /usage` with that key).
//! - **New runs (monthly):** the first successful append for a given `run_id` in the tenant ledger
//!   increments `new_run_ids` for the current UTC `year_month` bucket.
//! - **Per-run cap:** the event count for that `run_id` in the ledger **after** this append would be
//!   `next_count`; limits compare against that value.
//!
//! **Concurrency:** precheck reads aggregates then append writes the log; two concurrent requests can
//! in theory both pass precheck and append; DB counters in `record_successful_ingest` remain consistent
//! but could briefly exceed soft caps until the next request. Treat limits as **best-effort** without
//! cross-transaction ledger locking.

use crate::db::DbPool;
use crate::govai_environment::GovaiEnvironment;
use chrono::{Datelike, Utc};
use sqlx::Row;
use std::collections::HashMap;
use std::str::FromStr;
use uuid::Uuid;

pub const METERING_ENV_ON: &str = "on";

/// Env var holding declarative key_hash → team_id mapping for billing isolation.
/// Format: `{"<sha256_api_key_hash>": "<team_uuid>", ...}` (key_hash is the sha256 of the raw
/// bearer token, lowercase hex; same digest as [`crate::api_usage::key_fingerprint`]).
///
/// Provisioning behavior:
/// - In dev, the env var is optional. If absent or empty, no upserts are performed.
/// - In staging/prod, when the env var is present it must parse to a valid map; any
///   malformed entry (non-64-hex key_hash or non-UUID team_id) fails startup.
/// - Each entry is upserted into [`public.govai_api_key_billing`] with `on conflict (key_hash)
///   do update set team_id = excluded.team_id` so rotating the team_id is operationally safe.
/// - Raw API keys are NEVER stored — only their sha256 fingerprints.
/// - Ledger tenant isolation is unaffected; that remains derived from `GOVAI_API_KEYS_JSON`.
/// - Unlimited metering remains controlled by `GOVAI_UNLIMITED_METERING_TEAMS` (UUID set);
///   the team_id provisioned here is what that env var refers to.
pub const API_KEY_BILLING_TEAMS_ENV: &str = "GOVAI_API_KEY_BILLING_TEAMS_JSON";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MeteringConfig {
    pub enabled: bool,
    pub default_plan: GovaiPlan,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum GovaiPlan {
    Free,
    Team,
    Growth,
    Enterprise,
}

/// Monthly / per-run caps. `None` = unlimited (Enterprise).
#[derive(Clone, Copy, Debug)]
pub struct PlanLimits {
    pub max_runs_per_month: Option<u64>,
    pub max_events_per_month: Option<u64>,
    pub max_events_per_run: Option<u64>,
}

impl PlanLimits {
    pub fn for_plan(plan: GovaiPlan) -> Self {
        match plan {
            GovaiPlan::Free => Self {
                max_runs_per_month: Some(25),
                max_events_per_month: Some(2_500),
                max_events_per_run: Some(1_000),
            },
            GovaiPlan::Team => Self {
                max_runs_per_month: Some(500),
                max_events_per_month: Some(50_000),
                max_events_per_run: Some(5_000),
            },
            GovaiPlan::Growth => Self {
                max_runs_per_month: Some(2_500),
                max_events_per_month: Some(250_000),
                max_events_per_run: Some(10_000),
            },
            GovaiPlan::Enterprise => Self {
                max_runs_per_month: None,
                max_events_per_month: None,
                max_events_per_run: None,
            },
        }
    }
}

impl MeteringConfig {
    /// `GOVAI_METERING`: `off` (default) or `on`.
    /// `GOVAI_DEFAULT_PLAN`: `free` | `team` | `growth` | `enterprise` (default: free).
    pub fn from_env() -> Self {
        let enabled = std::env::var("GOVAI_METERING")
            .map(|s| s.trim().eq_ignore_ascii_case(METERING_ENV_ON))
            .unwrap_or(false);
        let default_plan = std::env::var("GOVAI_DEFAULT_PLAN")
            .map(|s| match s.trim().to_ascii_lowercase().as_str() {
                "team" => GovaiPlan::Team,
                "growth" => GovaiPlan::Growth,
                "enterprise" => GovaiPlan::Enterprise,
                _ => GovaiPlan::Free,
            })
            .unwrap_or(GovaiPlan::Free);
        Self {
            enabled,
            default_plan,
        }
    }
}

/// UTC `year * 100 + month` (e.g. 202604).
pub fn year_month_utc_now() -> i32 {
    let now = Utc::now().date_naive();
    now.year() * 100 + now.month() as i32
}

pub fn is_unlimited_metering_team(team_id: &Uuid) -> bool {
    let team_id = team_id.to_string();

    std::env::var("GOVAI_UNLIMITED_METERING_TEAMS")
        .unwrap_or_default()
        .split(',')
        .map(str::trim)
        .any(|candidate| !candidate.is_empty() && candidate == team_id)
}

pub fn run_complexity_label(event_count: u64) -> &'static str {
    match event_count {
        0..=100 => "light",
        101..=1_000 => "standard",
        1_001..=5_000 => "heavy",
        _ => "extreme",
    }
}

pub async fn team_id_for_key_hash(
    pool: &DbPool,
    key_hash: &str,
) -> Result<Option<Uuid>, sqlx::Error> {
    let row = sqlx::query(
        r#"
        select team_id
        from public.govai_api_key_billing
        where key_hash = $1
        "#,
    )
    .bind(key_hash)
    .fetch_optional(pool)
    .await?;
    Ok(row.map(|r| r.get("team_id")))
}

/// Parsed entry: `(key_hash, team_id)`. Validated to canonical form (lowercase hex / UUID).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ApiKeyBillingEntry {
    pub key_hash: String,
    pub team_id: Uuid,
}

fn is_64_lowercase_hex(s: &str) -> bool {
    s.len() == 64 && s.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'))
}

/// Parse `GOVAI_API_KEY_BILLING_TEAMS_JSON` into validated entries.
///
/// - Empty / whitespace-only input → `Ok(empty)`.
/// - Malformed JSON object → `Err`.
/// - Each entry's `key_hash` must be 64-char lowercase hex (sha256 fingerprint).
/// - Each entry's `team_id` must parse as a UUID.
/// - Raw API keys are never accepted; this function only handles fingerprints, never bearers.
pub fn parse_api_key_billing_teams_json(raw: &str) -> Result<Vec<ApiKeyBillingEntry>, String> {
    let raw = raw.trim();
    if raw.is_empty() {
        return Ok(Vec::new());
    }

    let parsed: HashMap<String, String> = serde_json::from_str(raw).map_err(|e| {
        format!(
            "Invalid {API_KEY_BILLING_TEAMS_ENV}: expected JSON object mapping <sha256_api_key_hash> -> <team_uuid> (got parse error: {e})"
        )
    })?;

    let mut out: Vec<ApiKeyBillingEntry> = Vec::with_capacity(parsed.len());
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();

    for (raw_hash, raw_team) in parsed.into_iter() {
        let hash = raw_hash.trim().to_string();
        let team = raw_team.trim().to_string();

        if !is_64_lowercase_hex(&hash) {
            return Err(format!(
                "Invalid {API_KEY_BILLING_TEAMS_ENV}: key_hash must be 64-char lowercase hex \
                 (sha256 fingerprint of the raw API key); got entry with invalid key_hash. \
                 Never store raw API keys."
            ));
        }
        let team_id = Uuid::from_str(&team).map_err(|e| {
            format!(
                "Invalid {API_KEY_BILLING_TEAMS_ENV}: team_id for one key_hash is not a valid UUID: {e}"
            )
        })?;

        if !seen.insert(hash.clone()) {
            return Err(format!(
                "Invalid {API_KEY_BILLING_TEAMS_ENV}: duplicate key_hash entry"
            ));
        }

        out.push(ApiKeyBillingEntry {
            key_hash: hash,
            team_id,
        });
    }

    Ok(out)
}

/// Read `GOVAI_API_KEY_BILLING_TEAMS_JSON` and upsert each `(key_hash, team_id)` entry into
/// `public.govai_api_key_billing`. Returns the number of upserted rows.
///
/// - Dev: missing/empty env var is allowed; malformed JSON still fails fast (operator typo
///   should not be silently swallowed).
/// - Staging/Prod: malformed JSON fails fast. Missing/empty env var is allowed (operator may
///   provision the table by other means, e.g. an admin migration), so existing deployments
///   are not broken if the env var is not yet adopted.
///
/// This function is idempotent: re-running with the same map is a no-op. Rotating a team_id
/// for an existing key_hash takes effect immediately.
/// Upsert a single issued API key hash → team mapping (self-service key issuance).
pub async fn upsert_api_key_billing_team(
    pool: &DbPool,
    key_hash: &str,
    team_id: uuid::Uuid,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        insert into public.govai_api_key_billing (key_hash, team_id)
        values ($1, $2)
        on conflict (key_hash) do update set team_id = excluded.team_id
        "#,
    )
    .bind(key_hash)
    .bind(team_id)
    .execute(pool)
    .await?;
    Ok(())
}

pub async fn provision_api_key_billing_teams_from_env(
    pool: &DbPool,
    deployment_env: GovaiEnvironment,
) -> Result<usize, String> {
    let raw = std::env::var(API_KEY_BILLING_TEAMS_ENV).unwrap_or_default();
    let entries = match parse_api_key_billing_teams_json(&raw) {
        Ok(v) => v,
        Err(e) => {
            return match deployment_env {
                GovaiEnvironment::Dev => {
                    // Even in dev we surface malformed JSON as an error; otherwise operator
                    // changes are silently ignored which is exactly the failure mode this
                    // feature exists to prevent.
                    Err(e)
                }
                GovaiEnvironment::Staging | GovaiEnvironment::Prod => Err(e),
            };
        }
    };

    if entries.is_empty() {
        return Ok(0);
    }

    let mut count = 0_usize;
    for entry in &entries {
        sqlx::query(
            r#"
            insert into public.govai_api_key_billing (key_hash, team_id)
            values ($1, $2)
            on conflict (key_hash) do update
              set team_id = excluded.team_id
            "#,
        )
        .bind(&entry.key_hash)
        .bind(entry.team_id)
        .execute(pool)
        .await
        .map_err(|e| {
            format!(
                "{API_KEY_BILLING_TEAMS_ENV} upsert failed for key_hash (sha256 fingerprint redacted): {e}"
            )
        })?;
        count += 1;
    }

    println!(
        "startup: api_key_billing_teams_provisioned count={count} (source={API_KEY_BILLING_TEAMS_ENV}; raw API keys NOT stored)"
    );
    Ok(count)
}

#[derive(Debug)]
pub enum MeteringReject {
    MonthlyRunLimit {
        used: u64,
        limit: u64,
    },
    MonthlyEventLimit {
        used: u64,
        limit: u64,
    },
    PerRunEventLimit {
        run_id: String,
        would_be: u64,
        limit: u64,
    },
}

/// Read current monthly row (missing row => zeros). No side effects.
pub async fn load_monthly(
    pool: &DbPool,
    team_id: Uuid,
    year_month: i32,
) -> Result<(i64, i64), sqlx::Error> {
    let row = sqlx::query(
        r#"
        select new_run_ids, evidence_events
        from public.govai_team_usage_monthly
        where team_id = $1 and year_month = $2
        "#,
    )
    .bind(team_id)
    .bind(year_month)
    .fetch_optional(pool)
    .await?;
    match row {
        None => Ok((0, 0)),
        Some(r) => Ok((r.get("new_run_ids"), r.get("evidence_events"))),
    }
}

/// Load non-billable operational counters (missing row => zeros).
pub async fn load_monthly_ops(
    pool: &DbPool,
    team_id: Uuid,
    year_month: i32,
) -> Result<(i64, i64, i64), sqlx::Error> {
    let row = sqlx::query(
        r#"
        select
          coalesce(compliance_checks, 0) as compliance_checks,
          coalesce(exports, 0) as exports,
          coalesce(discovery_scans, 0) as discovery_scans
        from public.govai_team_usage_monthly
        where team_id = $1 and year_month = $2
        "#,
    )
    .bind(team_id)
    .bind(year_month)
    .fetch_optional(pool)
    .await?;
    match row {
        None => Ok((0, 0, 0)),
        Some(r) => Ok((
            r.get("compliance_checks"),
            r.get("exports"),
            r.get("discovery_scans"),
        )),
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TeamOpCounter {
    ComplianceCheck,
    Export,
    DiscoveryScan,
}

/// Increment a single operational counter for the month (idempotency not attempted).
pub async fn increment_team_op_counter(
    pool: &DbPool,
    team_id: Uuid,
    year_month: i32,
    counter: TeamOpCounter,
) -> Result<(), String> {
    let (cc, ex, ds) = match counter {
        TeamOpCounter::ComplianceCheck => (1i64, 0i64, 0i64),
        TeamOpCounter::Export => (0i64, 1i64, 0i64),
        TeamOpCounter::DiscoveryScan => (0i64, 0i64, 1i64),
    };
    sqlx::query(
        r#"
        insert into public.govai_team_usage_monthly
          (team_id, year_month, compliance_checks, exports, discovery_scans, updated_at)
        values ($1, $2, $3, $4, $5, now())
        on conflict (team_id, year_month) do update set
          compliance_checks = public.govai_team_usage_monthly.compliance_checks + excluded.compliance_checks,
          exports = public.govai_team_usage_monthly.exports + excluded.exports,
          discovery_scans = public.govai_team_usage_monthly.discovery_scans + excluded.discovery_scans,
          updated_at = now()
        "#,
    )
    .bind(team_id)
    .bind(year_month)
    .bind(cc)
    .bind(ex)
    .bind(ds)
    .execute(pool)
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

/// Plan-limit guard before append when `GOVAI_METERING=on`. Reads [`load_monthly`] + ledger-derived
/// `next_count` / `is_new_run`; counters are persisted in [`record_successful_ingest`] after append.
pub fn precheck_ingest(
    plan: GovaiPlan,
    limits: PlanLimits,
    new_run_ids: i64,
    evidence_events: i64,
    is_new_run: bool,
    run_id: &str,
    next_count: u64,
    unlimited_monthly: bool,
) -> Result<(), MeteringReject> {
    if plan == GovaiPlan::Enterprise {
        return Ok(());
    }

    if let Some(lim) = limits.max_events_per_run {
        if next_count > lim {
            return Err(MeteringReject::PerRunEventLimit {
                run_id: run_id.to_string(),
                would_be: next_count,
                limit: lim,
            });
        }
    }

    if !unlimited_monthly {
        if let Some(lim) = limits.max_events_per_month {
            let next_ev = (evidence_events + 1).max(0) as u64;
            if next_ev > lim {
                return Err(MeteringReject::MonthlyEventLimit {
                    used: evidence_events.max(0) as u64,
                    limit: lim,
                });
            }
        }
    }

    if !unlimited_monthly && is_new_run {
        if let Some(lim) = limits.max_runs_per_month {
            let next_runs = (new_run_ids + 1).max(0) as u64;
            if next_runs > lim {
                return Err(MeteringReject::MonthlyRunLimit {
                    used: new_run_ids.max(0) as u64,
                    limit: lim,
                });
            }
        }
    }

    Ok(())
}

/// After successful ledger append, persist counters.
pub async fn record_successful_ingest(
    pool: &DbPool,
    team_id: Uuid,
    year_month: i32,
    run_id: &str,
    next_count: i64,
    is_new_run: bool,
) -> Result<(), String> {
    let mut tx = pool.begin().await.map_err(|e| e.to_string())?;

    let new_run_delta: i64 = if is_new_run { 1 } else { 0 };

    sqlx::query(
        r#"
        insert into public.govai_team_usage_monthly
          (team_id, year_month, new_run_ids, evidence_events, updated_at)
        values ($1, $2, $3, 1, now())
        on conflict (team_id, year_month) do update set
          new_run_ids = public.govai_team_usage_monthly.new_run_ids + excluded.new_run_ids,
          evidence_events = public.govai_team_usage_monthly.evidence_events + 1,
          updated_at = now()
        "#,
    )
    .bind(team_id)
    .bind(year_month)
    .bind(new_run_delta)
    .execute(&mut *tx)
    .await
    .map_err(|e| e.to_string())?;

    sqlx::query(
        r#"
        insert into public.govai_run_meters
          (run_id, team_id, event_count, first_ingest_at)
        values ($1, $2, $3, now())
        on conflict (run_id) do update set
          event_count = $3,
          team_id = $2
        "#,
    )
    .bind(run_id)
    .bind(team_id)
    .bind(next_count)
    .execute(&mut *tx)
    .await
    .map_err(|e| e.to_string())?;

    tx.commit().await.map_err(|e| e.to_string())?;
    Ok(())
}

/// Nearing limit warnings (80% of monthly events or runs) — basic UX.
/// `evidence_events_after` / `new_run_ids_after` are values **after** this successful ingest.
pub fn basic_warnings(
    plan: GovaiPlan,
    limits: PlanLimits,
    new_run_ids_after: i64,
    evidence_events_after: i64,
    is_new_run: bool,
    unlimited_monthly: bool,
) -> Vec<serde_json::Value> {
    if plan == GovaiPlan::Enterprise || unlimited_monthly {
        return vec![];
    }
    let mut w = vec![];
    if let Some(lim) = limits.max_events_per_month {
        let u = evidence_events_after.max(0) as f64;
        if (u / lim as f64) >= 0.8 {
            w.push(serde_json::json!({
                "code": "nearing_monthly_event_limit",
                "used": evidence_events_after.max(0),
                "limit": lim
            }));
        }
    }
    if let (Some(lim), true) = (limits.max_runs_per_month, is_new_run) {
        let u = new_run_ids_after.max(0) as f64;
        if (u / lim as f64) >= 0.8 {
            w.push(serde_json::json!({
                "code": "nearing_monthly_run_limit",
                "used": new_run_ids_after.max(0),
                "limit": lim
            }));
        }
    }
    w
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn precheck_blocks_per_run() {
        let l = PlanLimits::for_plan(GovaiPlan::Free);
        let e = precheck_ingest(GovaiPlan::Free, l, 0, 0, true, "r1", 1001, false);
        assert!(e.is_err());
    }

    #[test]
    fn precheck_unlimited_monthly_allows_free_plan_over_monthly_caps() {
        let l = PlanLimits::for_plan(GovaiPlan::Free);
        assert!(precheck_ingest(GovaiPlan::Free, l, 25, 2_500, true, "r1", 1, true).is_ok());
    }

    #[test]
    fn precheck_unlimited_monthly_keeps_per_run_cap() {
        let l = PlanLimits::for_plan(GovaiPlan::Free);
        let e = precheck_ingest(GovaiPlan::Free, l, 25, 2_500, false, "r1", 1_001, true);
        assert!(matches!(e, Err(MeteringReject::PerRunEventLimit { .. })));
    }

    #[test]
    fn precheck_allows_enterprise() {
        let l = PlanLimits::for_plan(GovaiPlan::Enterprise);
        assert!(
            precheck_ingest(GovaiPlan::Enterprise, l, 0, 0, true, "r1", 999_999, false,).is_ok()
        );
    }

    fn valid_hash() -> String {
        "0".repeat(64)
    }

    #[test]
    fn parse_api_key_billing_teams_json_empty_is_ok() {
        assert!(parse_api_key_billing_teams_json("").unwrap().is_empty());
        assert!(parse_api_key_billing_teams_json("   ").unwrap().is_empty());
    }

    #[test]
    fn parse_api_key_billing_teams_json_accepts_valid_entries() {
        let team = Uuid::new_v4();
        let raw = format!(r#"{{"{}":"{}"}}"#, valid_hash(), team);
        let parsed = parse_api_key_billing_teams_json(&raw).expect("valid input");
        assert_eq!(parsed.len(), 1);
        assert_eq!(parsed[0].key_hash, valid_hash());
        assert_eq!(parsed[0].team_id, team);
    }

    #[test]
    fn parse_api_key_billing_teams_json_rejects_malformed_json() {
        let err = parse_api_key_billing_teams_json("not-json").unwrap_err();
        assert!(err.contains(API_KEY_BILLING_TEAMS_ENV));
    }

    #[test]
    fn parse_api_key_billing_teams_json_rejects_invalid_key_hash() {
        let team = Uuid::new_v4();
        // Uppercase hex is rejected (we require canonical lowercase).
        let bad = format!(r#"{{"{}":"{}"}}"#, "A".repeat(64), team);
        let err = parse_api_key_billing_teams_json(&bad).unwrap_err();
        assert!(
            err.contains("64-char lowercase hex"),
            "expected hex error, got: {err}"
        );
        // Wrong length is rejected.
        let bad2 = format!(r#"{{"{}":"{}"}}"#, "0".repeat(63), team);
        let err = parse_api_key_billing_teams_json(&bad2).unwrap_err();
        assert!(err.contains("64-char lowercase hex"), "got: {err}");
    }

    #[test]
    fn parse_api_key_billing_teams_json_rejects_invalid_team_uuid() {
        let bad = format!(r#"{{"{}":"not-a-uuid"}}"#, valid_hash());
        let err = parse_api_key_billing_teams_json(&bad).unwrap_err();
        assert!(err.contains("not a valid UUID"), "got: {err}");
    }
}
