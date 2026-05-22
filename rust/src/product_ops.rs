//! Persisted product analytics, autonomy policy rows, tenant health, and team↔ledger bindings.

use crate::autonomous_runtime::{
    autonomy_enforcement_enabled_from_env, evaluate_autonomous_action,
    extract_autonomous_capability_from_payload, LoadedAutonomyPolicy,
};
use crate::db::DbPool;
use crate::schema::EvidenceEvent;
use chrono::{DateTime, Utc};
use serde_json::{json, Value};
use sqlx::Row;
use uuid::Uuid;

#[derive(Debug, Clone)]
pub struct AutonomyPolicyRow {
    pub ledger_tenant_id: String,
    pub autonomy_level: i16,
    pub allowed_capabilities: Vec<String>,
    pub required_human_roles: Vec<String>,
    pub requires_approval: bool,
    pub requires_dual_approval: bool,
    pub requires_override_reference: bool,
    pub stop_controls_enabled: bool,
    pub kill_switch_enabled: bool,
    pub emergency_stop_engaged: bool,
    pub kill_switch_engaged: bool,
}

impl From<AutonomyPolicyRow> for LoadedAutonomyPolicy {
    fn from(r: AutonomyPolicyRow) -> Self {
        LoadedAutonomyPolicy {
            autonomy_level: r.autonomy_level,
            allowed_capabilities: r.allowed_capabilities,
            required_human_roles: r.required_human_roles,
            requires_approval: r.requires_approval,
            requires_dual_approval: r.requires_dual_approval,
            requires_override_reference: r.requires_override_reference,
            stop_controls_enabled: r.stop_controls_enabled,
            kill_switch_enabled: r.kill_switch_enabled,
            emergency_stop_engaged: r.emergency_stop_engaged,
            kill_switch_engaged: r.kill_switch_engaged,
        }
    }
}

pub async fn load_autonomy_policy(
    pool: &DbPool,
    ledger_tenant_id: &str,
) -> Result<Option<AutonomyPolicyRow>, sqlx::Error> {
    let row = sqlx::query(
        r#"
        select
          ledger_tenant_id,
          autonomy_level,
          coalesce(allowed_capabilities, array[]::text[]) as allowed_capabilities,
          coalesce(required_human_roles, array[]::text[]) as required_human_roles,
          requires_approval,
          requires_dual_approval,
          requires_override_reference,
          stop_controls_enabled,
          kill_switch_enabled,
          emergency_stop_engaged,
          kill_switch_engaged
        from public.govai_tenant_autonomy_policy
        where ledger_tenant_id = $1
        "#,
    )
    .bind(ledger_tenant_id)
    .fetch_optional(pool)
    .await?;

    let Some(r) = row else {
        return Ok(None);
    };
    let caps: Vec<String> = r.get::<Vec<String>, _>("allowed_capabilities");
    let roles: Vec<String> = r.get::<Vec<String>, _>("required_human_roles");
    Ok(Some(AutonomyPolicyRow {
        ledger_tenant_id: r.get("ledger_tenant_id"),
        autonomy_level: r.get("autonomy_level"),
        allowed_capabilities: caps,
        required_human_roles: roles,
        requires_approval: r.get("requires_approval"),
        requires_dual_approval: r.get("requires_dual_approval"),
        requires_override_reference: r.get("requires_override_reference"),
        stop_controls_enabled: r.get("stop_controls_enabled"),
        kill_switch_enabled: r.get("kill_switch_enabled"),
        emergency_stop_engaged: r.get("emergency_stop_engaged"),
        kill_switch_engaged: r.get("kill_switch_engaged"),
    }))
}

/// Reject ingest when autonomy enforcement is enabled, the payload requests autonomous execution,
/// and the evaluation is not permitted (fail-closed when policy row is missing).
pub async fn ingest_autonomy_gate(
    pool: &DbPool,
    ledger_tenant_id: &str,
    event: &EvidenceEvent,
) -> Result<(), String> {
    if !autonomy_enforcement_enabled_from_env() {
        return Ok(());
    }
    let Some((cap, stop, kill)) = extract_autonomous_capability_from_payload(&event.payload) else {
        return Ok(());
    };

    let row = load_autonomy_policy(pool, ledger_tenant_id)
        .await
        .map_err(|e| e.to_string())?;
    let Some(policy_row) = row else {
        return Err(format!(
            "AUTONOMY_POLICY_REQUIRED: ledger_tenant_id={ledger_tenant_id} has no govai_tenant_autonomy_policy row"
        ));
    };
    let policy: LoadedAutonomyPolicy = policy_row.into();
    let out = evaluate_autonomous_action(&policy, &cap, stop, kill);
    if out.permitted {
        Ok(())
    } else {
        Err(format!(
            "AUTONOMY_BLOCKED: {}",
            out.blocked_reason_codes.join(",")
        ))
    }
}

/// Returns `true` when a new milestone row was inserted.
pub async fn try_record_first_milestone(
    pool: &DbPool,
    ledger_tenant_id: &str,
    event_type: &str,
    run_id: Option<&str>,
    payload: Value,
) -> Result<bool, sqlx::Error> {
    if !event_type.starts_with("first_") {
        return Ok(false);
    }
    let id = Uuid::new_v4();
    let res = sqlx::query(
        r#"
        insert into public.govai_product_events (id, ledger_tenant_id, event_type, run_id, payload)
        select $1::uuid, $2, $3, $4, $5
        where not exists (
          select 1 from public.govai_product_events e
          where e.ledger_tenant_id = $2 and e.event_type = $3
        )
        "#,
    )
    .bind(id)
    .bind(ledger_tenant_id)
    .bind(event_type)
    .bind(run_id)
    .bind(payload)
    .execute(pool)
    .await?;
    Ok(res.rows_affected() > 0)
}

pub async fn list_product_events_for_tenant(
    pool: &DbPool,
    ledger_tenant_id: &str,
    limit: i64,
) -> Result<Vec<Value>, sqlx::Error> {
    let rows = sqlx::query(
        r#"
        select event_type, run_id, payload, created_at
        from public.govai_product_events
        where ledger_tenant_id = $1
        order by created_at desc
        limit $2
        "#,
    )
    .bind(ledger_tenant_id)
    .bind(limit)
    .fetch_all(pool)
    .await?;

    let mut out = Vec::new();
    for r in rows {
        out.push(json!({
            "event_type": r.get::<String, _>("event_type"),
            "run_id": r.try_get::<Option<String>, _>("run_id").ok().flatten(),
            "payload": r.get::<Value, _>("payload"),
            "created_at": r.get::<DateTime<Utc>, _>("created_at").to_rfc3339(),
        }));
    }
    Ok(out)
}

pub async fn get_ledger_tenant_for_team(
    pool: &DbPool,
    team_id: Uuid,
) -> Result<Option<String>, sqlx::Error> {
    sqlx::query_scalar::<_, String>(
        r#"
        select ledger_tenant_id
        from public.govai_team_ledger_bindings
        where team_id = $1
        "#,
    )
    .bind(team_id)
    .fetch_optional(pool)
    .await
}

pub async fn upsert_team_ledger_binding(
    pool: &DbPool,
    team_id: Uuid,
    ledger_tenant_id: &str,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"
        insert into public.govai_team_ledger_bindings (team_id, ledger_tenant_id)
        values ($1, $2)
        on conflict (team_id) do update set ledger_tenant_id = excluded.ledger_tenant_id
        "#,
    )
    .bind(team_id)
    .bind(ledger_tenant_id)
    .execute(pool)
    .await?;
    Ok(())
}

/// Heuristic health score from billing + milestones (best-effort; safe on empty DB).
pub async fn recompute_tenant_health(
    pool: &DbPool,
    ledger_tenant_id: &str,
) -> Result<(), sqlx::Error> {
    let m_count: i64 = sqlx::query_scalar(
        r#"
        select count(*)::bigint
        from public.govai_product_events
        where ledger_tenant_id = $1 and event_type ~ '^first_'
        "#,
    )
    .bind(ledger_tenant_id)
    .fetch_one(pool)
    .await?;

    let ingest_n: i64 = match sqlx::query_scalar(
        r#"
        select count(*)::bigint
        from public.govai_billing_usage_trace
        where ledger_tenant_id = $1
        "#,
    )
    .bind(ledger_tenant_id)
    .fetch_one(pool)
    .await
    {
        Ok(n) => n,
        Err(_) => 0,
    };

    let sub: Option<String> = sqlx::query_scalar(
        r#"
        select subscription_status
        from public.tenant_billing_accounts
        where tenant_id = $1
        "#,
    )
    .bind(ledger_tenant_id)
    .fetch_optional(pool)
    .await?;

    let active = sub
        .as_deref()
        .map(|s| matches!(s.to_ascii_lowercase().as_str(), "active" | "trialing"))
        .unwrap_or(false);

    let mut score: i32 = (m_count * 12).min(60) as i32;
    if ingest_n > 0 {
        score += 15;
    }
    if active {
        score += 25;
    }
    score = score.clamp(0, 100);

    let renewal_risk = if active { "low" } else { "elevated" }.to_string();
    let mut signals = Vec::new();
    if ingest_n >= 10 {
        signals.push(json!({"signal": "sustained_evidence_volume"}));
    }
    if m_count >= 4 {
        signals.push(json!({"signal": "activation_depth"}));
    }

    sqlx::query(
        r#"
        insert into public.govai_tenant_health (
          ledger_tenant_id, health_score, renewal_risk, expansion_signals, computed_at
        )
        values ($1, $2, $3, $4, now())
        on conflict (ledger_tenant_id) do update set
          health_score = excluded.health_score,
          renewal_risk = excluded.renewal_risk,
          expansion_signals = excluded.expansion_signals,
          computed_at = excluded.computed_at
        "#,
    )
    .bind(ledger_tenant_id)
    .bind(score)
    .bind(&renewal_risk)
    .bind(Value::Array(signals))
    .execute(pool)
    .await?;

    Ok(())
}

pub async fn get_tenant_health_row(
    pool: &DbPool,
    ledger_tenant_id: &str,
) -> Result<Option<Value>, sqlx::Error> {
    let row = sqlx::query(
        r#"
        select ledger_tenant_id, health_score, renewal_risk, expansion_signals, computed_at
        from public.govai_tenant_health
        where ledger_tenant_id = $1
        "#,
    )
    .bind(ledger_tenant_id)
    .fetch_optional(pool)
    .await?;

    let Some(r) = row else {
        return Ok(None);
    };
    Ok(Some(json!({
        "ledger_tenant_id": r.get::<String, _>("ledger_tenant_id"),
        "health_score": r.get::<i32, _>("health_score"),
        "renewal_risk": r.get::<String, _>("renewal_risk"),
        "expansion_signals": r.get::<Value, _>("expansion_signals"),
        "computed_at": r.get::<DateTime<Utc>, _>("computed_at").to_rfc3339(),
    })))
}

pub fn crm_export_jsonl(events: &[Value], health: Option<Value>) -> String {
    let mut lines = String::new();
    if let Some(h) = health {
        lines.push_str(&format!(
            "{}\n",
            serde_json::to_string(&h).unwrap_or_default()
        ));
    }
    for e in events {
        lines.push_str(&format!(
            "{}\n",
            serde_json::to_string(e).unwrap_or_default()
        ));
    }
    lines
}
