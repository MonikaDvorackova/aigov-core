//! Append-only AI decision and multi-agent trace storage (Postgres).
//!
//! This layer records **operational telemetry** for AI runs (models, hashes, agents, tools, policy checks,
//! human gates). The **immutable ledger compliance verdict** for a run remains authoritative only from
//! **`GET /compliance-summary`**. Optional `compliance_summary_run_id` in `trace_started` links the same
//! business `run_id` when operators align identifiers.

use crate::ai_decision_integrity::{
    self, analyze_delegation_dag, canonical_payload_digest_hex, event_hash_hex,
    explainability_summary_from_events, human_workflow_export, merge_completed_for_verdict,
    verdict_detail, verify_integrity_from_api_events, DIGEST_CANONICAL, GENESIS_PREV,
};
use crate::db::DbPool;
use chrono::{DateTime, SecondsFormat, Utc};
use serde_json::{json, Value};
use sqlx::Row;
use uuid::Uuid;

const MAX_RUN_ID_LEN: usize = 256;

pub fn normalize_run_id(raw: &str) -> Result<String, String> {
    let t = raw.trim();
    if t.is_empty() {
        return Err("run_id is required".into());
    }
    if t.len() > MAX_RUN_ID_LEN {
        return Err(format!("run_id exceeds {MAX_RUN_ID_LEN} characters"));
    }
    Ok(t.to_string())
}

pub async fn trace_has_started_event(
    pool: &DbPool,
    ledger_tenant_id: &str,
    run_id: &str,
) -> Result<bool, sqlx::Error> {
    let n: i64 = sqlx::query_scalar(
        r#"
        select count(*)::bigint
        from public.govai_ai_decision_trace_events
        where ledger_tenant_id = $1 and run_id = $2 and event_type = 'trace_started'
        "#,
    )
    .bind(ledger_tenant_id)
    .bind(run_id)
    .fetch_one(pool)
    .await?;
    Ok(n > 0)
}

pub async fn insert_trace_event(
    pool: &DbPool,
    ledger_tenant_id: &str,
    team_id: Option<Uuid>,
    run_id: &str,
    correlation_id: Option<&str>,
    event_type: &str,
    payload: Value,
) -> Result<Uuid, sqlx::Error> {
    let mut tx = pool.begin().await?;
    let last = sqlx::query(
        r#"
        select event_seq, event_hash
        from public.govai_ai_decision_trace_events
        where ledger_tenant_id = $1 and run_id = $2
        order by event_seq desc
        limit 1
        for update
        "#,
    )
    .bind(ledger_tenant_id)
    .bind(run_id)
    .fetch_optional(&mut *tx)
    .await?;

    let (next_seq, prev_hash): (i64, String) = match last {
        None => (1i64, GENESIS_PREV.to_string()),
        Some(r) => (
            r.get::<i64, _>("event_seq") + 1,
            r.get::<String, _>("event_hash"),
        ),
    };

    let ts: DateTime<Utc> = sqlx::query_scalar("select clock_timestamp()")
        .fetch_one(&mut *tx)
        .await?;

    let digest = canonical_payload_digest_hex(&payload);
    let ms = ts.timestamp_millis();
    let ev_hash = event_hash_hex(
        ledger_tenant_id,
        run_id,
        next_seq,
        event_type,
        &digest,
        &prev_hash,
        ms,
    );

    let id = Uuid::new_v4();
    sqlx::query(
        r#"
        insert into public.govai_ai_decision_trace_events
          (id, ledger_tenant_id, team_id, run_id, correlation_id, event_type, payload,
           created_at, event_seq, canonical_payload_digest, previous_event_hash, event_hash,
           payload_digest_algorithm)
        values ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        "#,
    )
    .bind(id)
    .bind(ledger_tenant_id)
    .bind(team_id)
    .bind(run_id)
    .bind(correlation_id)
    .bind(event_type)
    .bind(payload)
    .bind(ts)
    .bind(next_seq)
    .bind(&digest)
    .bind(&prev_hash)
    .bind(&ev_hash)
    .bind(DIGEST_CANONICAL)
    .execute(&mut *tx)
    .await?;
    tx.commit().await?;
    Ok(id)
}

pub async fn list_events_for_run_ordered(
    pool: &DbPool,
    ledger_tenant_id: &str,
    run_id: &str,
) -> Result<Vec<Value>, sqlx::Error> {
    let rows = sqlx::query(
        r#"
        select id, event_type, payload, correlation_id, created_at,
               event_seq, canonical_payload_digest, previous_event_hash, event_hash,
               payload_digest_algorithm
        from public.govai_ai_decision_trace_events
        where ledger_tenant_id = $1 and run_id = $2
        order by event_seq asc, id asc
        "#,
    )
    .bind(ledger_tenant_id)
    .bind(run_id)
    .fetch_all(pool)
    .await?;

    let mut out = Vec::new();
    for r in rows {
        out.push(json!({
            "id": r.get::<Uuid, _>("id").to_string(),
            "event_type": r.get::<String, _>("event_type"),
            "payload": r.get::<Value, _>("payload"),
            "correlation_id": r.try_get::<Option<String>, _>("correlation_id").ok().flatten(),
            "created_at": r.get::<DateTime<Utc>, _>("created_at").to_rfc3339_opts(chrono::SecondsFormat::Millis, true),
            "event_seq": r.get::<i64, _>("event_seq"),
            "canonical_payload_digest": r.get::<String, _>("canonical_payload_digest"),
            "previous_event_hash": r.get::<String, _>("previous_event_hash"),
            "event_hash": r.get::<String, _>("event_hash"),
            "payload_digest_algorithm": r.get::<String, _>("payload_digest_algorithm"),
        }));
    }
    Ok(out)
}

pub fn preview_completed_verdict_detail(
    existing_events: &[Value],
    completed_payload: &Value,
) -> Value {
    let merged = merge_completed_for_verdict(existing_events, completed_payload);
    verdict_detail(&merged)
}

/// One row per distinct `run_id` (latest activity first), merged from `trace_started` + latest `completed`.
pub async fn list_recent_run_summaries(
    pool: &DbPool,
    ledger_tenant_id: &str,
    limit: i64,
) -> Result<Vec<Value>, sqlx::Error> {
    let rows = sqlx::query(
        r#"
        select
          e.run_id,
          max(e.created_at) as last_at,
          (
            select correlation_id from public.govai_ai_decision_trace_events e2
            where e2.ledger_tenant_id = $1 and e2.run_id = e.run_id and e2.event_type = 'trace_started'
            order by e2.event_seq asc limit 1
          ) as correlation_id,
          (
            select payload from public.govai_ai_decision_trace_events e2
            where e2.ledger_tenant_id = $1 and e2.run_id = e.run_id and e2.event_type = 'trace_started'
            order by e2.event_seq asc limit 1
          ) as started_payload,
          (
            select payload from public.govai_ai_decision_trace_events e3
            where e3.ledger_tenant_id = $1 and e3.run_id = e.run_id and e3.event_type = 'completed'
            order by e3.event_seq desc limit 1
          ) as completed_payload,
          (
            select payload from public.govai_ai_decision_trace_events e5
            where e5.ledger_tenant_id = $1 and e5.run_id = e.run_id and e5.event_type = 'human_gate'
            order by e5.event_seq desc limit 1
          ) as human_payload
        from public.govai_ai_decision_trace_events e
        where e.ledger_tenant_id = $1
        group by e.run_id
        order by max(e.created_at) desc
        limit $2
        "#,
    )
    .bind(ledger_tenant_id)
    .bind(limit)
    .fetch_all(pool)
    .await?;

    let mut out = Vec::new();
    for r in rows {
        let run_id: String = r.get("run_id");
        let last_at: DateTime<Utc> = r.get("last_at");
        let correlation_id: Option<String> = r.try_get("correlation_id").ok().flatten();
        let started: Value = r
            .try_get::<Option<Value>, _>("started_payload")
            .ok()
            .flatten()
            .unwrap_or(json!({}));
        let completed: Option<Value> = r.try_get("completed_payload").ok().flatten();

        let final_verdict = completed
            .as_ref()
            .and_then(|p| p.get("final_audit_verdict"))
            .and_then(|v| v.as_str())
            .map(|s| s.to_string());

        let model_provider = started
            .get("model_provider")
            .and_then(|v| v.as_str())
            .map(str::to_string);
        let model_name = started
            .get("model_name")
            .and_then(|v| v.as_str())
            .map(str::to_string);
        let root_agent_id = started
            .get("agent_id")
            .and_then(|v| v.as_str())
            .unwrap_or("");

        let human_payload: Option<Value> = r.try_get("human_payload").ok().flatten();
        let (human_approval, human_override) = if let Some(ref p) = human_payload {
            (
                p.get("approval_state")
                    .and_then(|v| v.as_str())
                    .map(str::to_string),
                p.get("override_state")
                    .and_then(|v| v.as_str())
                    .map(str::to_string),
            )
        } else {
            (None, None)
        };

        let events = list_events_for_run_ordered(pool, ledger_tenant_id, &run_id).await?;
        let (int_status, int_detail) =
            verify_integrity_from_api_events(ledger_tenant_id, &run_id, &events);
        let verdict = verdict_detail(&events);
        let delegations: Vec<Value> = events
            .iter()
            .filter(|e| e.get("event_type").and_then(|x| x.as_str()) == Some("delegation"))
            .map(|e| e.get("payload").cloned().unwrap_or(json!({})))
            .collect();
        let dag = analyze_delegation_dag(root_agent_id, &delegations);
        let explain = explainability_summary_from_events(&events);
        let derived = verdict
            .get("derived_audit_verdict")
            .and_then(|v| v.as_str())
            .unwrap_or("UNKNOWN");
        let risk = json!({
            "integrity_broken": int_status != ai_decision_integrity::IntegrityStatus::Ok,
            "delegation_invalid": !dag.delegation_chain_valid,
            "verdict_inconsistent": verdict["verdict_consistent"].as_bool() == Some(false),
            "policy_blocked": derived == "BLOCKED",
        });

        out.push(json!({
            "run_id": run_id,
            "correlation_id": correlation_id,
            "last_event_at": last_at.to_rfc3339_opts(SecondsFormat::Millis, true),
            "final_audit_verdict": final_verdict,
            "model_provider": model_provider,
            "model_name": model_name,
            "delegation_chain_depth": dag.delegation_chain_depth,
            "delegation_chain_valid": dag.delegation_chain_valid,
            "delegation_cycle_detected": dag.delegation_cycle_detected,
            "missing_parent_or_root": dag.missing_parent_or_root,
            "duplicate_delegation_edges": dag.duplicate_edge_count,
            "human_approval_state": human_approval,
            "human_override_state": human_override,
            "trace_integrity_status": int_status.as_str(),
            "trace_integrity_detail": int_detail,
            "derived_audit_verdict": verdict["derived_audit_verdict"],
            "producer_final_audit_verdict": verdict["producer_final_audit_verdict"],
            "verdict_consistent": verdict["verdict_consistent"],
            "explainability_summary": explain,
            "risk_indicators": risk,
        }));
    }
    Ok(out)
}

fn collect_delegation_edges(events: &[Value]) -> Vec<Value> {
    events
        .iter()
        .filter(|e| e.get("event_type").and_then(|x| x.as_str()) == Some("delegation"))
        .map(|e| e.get("payload").cloned().unwrap_or(json!({})))
        .collect()
}

fn last_human_payload(events: &[Value]) -> Value {
    for e in events.iter().rev() {
        if e.get("event_type").and_then(|x| x.as_str()) == Some("human_gate") {
            return e.get("payload").cloned().unwrap_or(json!({}));
        }
    }
    json!({})
}

/// Stable export document (`trace_version` 2): integrity, verdict derivation, delegation DAG,
/// explainability, and `govai_functions_v2` extensions (appeals, incidents, seals, certification marks, and related governance telemetry).
pub fn aggregate_trace_export(ledger_tenant_id: &str, run_id: &str, events: &[Value]) -> Value {
    let mut model = json!({"provider": Value::Null, "name": Value::Null, "version": Value::Null});
    let mut hashes = json!({"prompt": Value::Null, "input": Value::Null, "output": Value::Null});
    let mut root_agent = json!({"agent_id": Value::Null, "agent_role": Value::Null});
    let mut delegations: Vec<Value> = Vec::new();
    let mut tool_calls: Vec<Value> = Vec::new();
    let mut steps: Vec<Value> = Vec::new();
    let mut policies: Vec<Value> = Vec::new();
    let mut human = json!({"approval_state": "unknown", "override_state": "none"});
    let mut correlation_id: Option<String> = None;
    let mut compliance_summary_run_id: Option<String> = None;
    let mut final_verdict = json!("UNKNOWN");
    let raw_events: Vec<Value> = events.to_vec();
    let mut v2_approval_steps: Vec<Value> = Vec::new();
    let mut v2_appeals: Vec<Value> = Vec::new();
    let mut v2_incidents: Vec<Value> = Vec::new();
    let mut v2_remediations: Vec<Value> = Vec::new();
    let mut v2_monitoring: Vec<Value> = Vec::new();
    let mut v2_seals: Vec<Value> = Vec::new();
    let mut v2_legal_refs: Vec<Value> = Vec::new();
    let mut v2_certs: Vec<Value> = Vec::new();
    let mut v2_business: Vec<Value> = Vec::new();
    let mut v2_exec_briefs: Vec<Value> = Vec::new();

    for e in events {
        let et = e.get("event_type").and_then(|x| x.as_str()).unwrap_or("");
        let payload = e.get("payload").cloned().unwrap_or(json!({}));
        if let Some(c) = e.get("correlation_id").and_then(|x| x.as_str()) {
            if !c.is_empty() {
                correlation_id = Some(c.to_string());
            }
        }
        match et {
            "trace_started" => {
                model = json!({
                    "provider": payload.get("model_provider").cloned().unwrap_or(Value::Null),
                    "name": payload.get("model_name").cloned().unwrap_or(Value::Null),
                    "version": payload.get("model_version").cloned().unwrap_or(Value::Null),
                });
                hashes = json!({
                    "prompt": payload.get("prompt_hash").cloned().unwrap_or(Value::Null),
                    "input": payload.get("input_hash").cloned().unwrap_or(Value::Null),
                    "output": payload.get("output_hash").cloned().unwrap_or(Value::Null),
                });
                root_agent = json!({
                    "agent_id": payload.get("agent_id").cloned().unwrap_or(Value::Null),
                    "agent_role": payload.get("agent_role").cloned().unwrap_or(Value::Null),
                });
                if let Some(s) = payload
                    .get("compliance_summary_run_id")
                    .and_then(|x| x.as_str())
                {
                    compliance_summary_run_id = Some(s.to_string());
                }
                if correlation_id.is_none() {
                    correlation_id = e
                        .get("correlation_id")
                        .and_then(|x| x.as_str())
                        .map(|s| s.to_string());
                }
            }
            "delegation" => {
                delegations.push(json!({
                    "parent_agent_id": payload.get("parent_agent_id"),
                    "child_agent_id": payload.get("child_agent_id"),
                    "child_role": payload.get("child_role"),
                }));
            }
            "tool_call" => {
                tool_calls.push(json!({
                    "tool_name": payload.get("tool_name"),
                    "input_hash": payload.get("input_hash"),
                    "output_hash": payload.get("output_hash"),
                }));
            }
            "step" => {
                steps.push(json!({
                    "step_index": payload.get("step_index"),
                    "label": payload.get("label"),
                    "content_hash": payload.get("content_hash"),
                }));
            }
            "policy_eval" => {
                policies.push(json!({
                    "policy_id": payload.get("policy_id"),
                    "policy_version": payload.get("policy_version"),
                    "outcome": payload.get("outcome"),
                    "reason_codes": payload.get("reason_codes").cloned().unwrap_or(json!([])),
                    "triggered_controls": payload.get("triggered_controls").cloned().unwrap_or(json!([])),
                    "evidence_refs": payload.get("evidence_refs").cloned().unwrap_or(json!([])),
                    "decision_rationale": payload.get("decision_rationale"),
                    "explanation_summary": payload.get("explanation_summary"),
                }));
            }
            "human_gate" => {
                human = json!({
                    "approval_state": payload.get("approval_state").cloned().unwrap_or(json!("unknown")),
                    "override_state": payload.get("override_state").cloned().unwrap_or(json!("none")),
                    "approver_principal": payload.get("approver_principal"),
                    "approver_identity_hash": payload.get("approver_identity_hash"),
                    "approval_reason": payload.get("approval_reason"),
                    "approval_timestamp": payload.get("approval_timestamp"),
                });
            }
            "completed" => {
                if let Some(v) = payload.get("final_audit_verdict").and_then(|x| x.as_str()) {
                    final_verdict = json!(v);
                }
                if let Some(oh) = payload.get("output_hash") {
                    hashes["output"] = oh.clone();
                }
            }
            "approval_step" => {
                v2_approval_steps.push(payload.clone());
            }
            "appeal" => {
                v2_appeals.push(payload.clone());
            }
            "incident" => {
                v2_incidents.push(payload.clone());
            }
            "remediation" => {
                v2_remediations.push(payload.clone());
            }
            "monitoring_sample" => {
                v2_monitoring.push(payload.clone());
            }
            "seal_attestation" => {
                v2_seals.push(payload.clone());
            }
            "legal_evidence_ref" => {
                v2_legal_refs.push(payload.clone());
            }
            "certification_mark" => {
                v2_certs.push(payload.clone());
            }
            "business_impact" => {
                v2_business.push(payload.clone());
            }
            "executive_brief" => {
                v2_exec_briefs.push(payload.clone());
            }
            _ => {}
        }
    }

    let root_id = root_agent
        .get("agent_id")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let edges = collect_delegation_edges(events);
    let dag = analyze_delegation_dag(root_id, &edges);
    let (int_status, int_detail) =
        verify_integrity_from_api_events(ledger_tenant_id, run_id, events);
    let verdict = verdict_detail(events);
    let explain = explainability_summary_from_events(events);
    let human_last = last_human_payload(events);
    let human_workflow = human_workflow_export(&human_last, &verdict);
    let derived = verdict
        .get("derived_audit_verdict")
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN");
    let risk = json!({
        "integrity_broken": int_status != ai_decision_integrity::IntegrityStatus::Ok,
        "delegation_invalid": !dag.delegation_chain_valid,
        "verdict_inconsistent": verdict["verdict_consistent"].as_bool() == Some(false),
        "policy_blocked": derived == "BLOCKED",
    });

    json!({
        "ok": true,
        "trace_version": 2,
        "ledger_tenant_id": ledger_tenant_id,
        "run_id": run_id,
        "correlation_id": correlation_id,
        "compliance_summary_run_id": compliance_summary_run_id,
        "relation_to_compliance_summary": "Immutable ledger compliance verdict for the same logical run is only authoritative from GET /compliance-summary. This document is append-only AI operational telemetry (flight recorder) stored in Postgres.",
        "model": model,
        "hashes": hashes,
        "agents": {
            "root": root_agent,
            "delegations": delegations,
            "delegation_graph": dag.to_json(),
        },
        "tool_calls": tool_calls,
        "steps": steps,
        "policies_evaluated": policies,
        "human": human,
        "human_approval_workflow": human_workflow,
        "final_audit_verdict": final_verdict,
        "derived_audit_verdict": verdict["derived_audit_verdict"],
        "producer_final_audit_verdict": verdict["producer_final_audit_verdict"],
        "verdict_consistent": verdict["verdict_consistent"],
        "trace_integrity": {
            "status": int_status.as_str(),
            "detail": int_detail,
        },
        "explainability": explain,
        "risk_indicators": risk,
        "govai_functions_v2": {
            "schema_version": "aigov.functions_v2.extensions.v1",
            "approval_steps": v2_approval_steps,
            "appeals": v2_appeals,
            "incidents": v2_incidents,
            "remediations": v2_remediations,
            "monitoring_samples": v2_monitoring,
            "seal_attestations": v2_seals,
            "legal_evidence_refs": v2_legal_refs,
            "certification_marks": v2_certs,
            "business_impacts": v2_business,
            "executive_briefs": v2_exec_briefs,
        },
        "events": raw_events,
    })
}

/// Backwards-compatible name; returns [`aggregate_trace_export`] (`trace_version` 2).
pub fn aggregate_trace_export_v1(ledger_tenant_id: &str, run_id: &str, events: &[Value]) -> Value {
    aggregate_trace_export(ledger_tenant_id, run_id, events)
}

pub fn validate_trace_started_payload(payload: &Value) -> Result<(), String> {
    for key in [
        "model_provider",
        "model_name",
        "prompt_hash",
        "input_hash",
        "agent_id",
        "agent_role",
    ] {
        let s = payload
            .get(key)
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim();
        if s.is_empty() {
            return Err(format!("trace_started.payload.{key} is required"));
        }
    }
    Ok(())
}

fn json_string_array_ok(v: &Value, field: &str) -> Result<(), String> {
    if v.is_null() {
        return Ok(());
    }
    let Some(a) = v.as_array() else {
        return Err(format!("{field} must be a JSON array of strings"));
    };
    for item in a {
        if !item.is_string() {
            return Err(format!("{field} entries must be strings"));
        }
    }
    Ok(())
}

pub fn validate_append_event(event_type: &str, payload: &Value) -> Result<(), String> {
    match event_type {
        "delegation" => {
            for k in ["parent_agent_id", "child_agent_id", "child_role"] {
                if payload
                    .get(k)
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .trim()
                    .is_empty()
                {
                    return Err(format!("delegation.payload.{k} is required"));
                }
            }
        }
        "tool_call" => {
            if payload
                .get("tool_name")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim()
                .is_empty()
            {
                return Err("tool_call.payload.tool_name is required".into());
            }
        }
        "step" => {
            if payload.get("step_index").and_then(|v| v.as_i64()).is_none() {
                return Err("step.payload.step_index must be an integer".into());
            }
        }
        "policy_eval" => {
            let out = payload
                .get("outcome")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            if !matches!(out, "allow" | "block" | "warn") {
                return Err("policy_eval.payload.outcome must be allow|block|warn".into());
            }
            if payload
                .get("policy_id")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim()
                .is_empty()
            {
                return Err("policy_eval.payload.policy_id is required".into());
            }
            json_string_array_ok(
                &payload.get("reason_codes").cloned().unwrap_or(json!([])),
                "reason_codes",
            )?;
            json_string_array_ok(
                &payload
                    .get("triggered_controls")
                    .cloned()
                    .unwrap_or(json!([])),
                "triggered_controls",
            )?;
            json_string_array_ok(
                &payload.get("evidence_refs").cloned().unwrap_or(json!([])),
                "evidence_refs",
            )?;
            if let Some(s) = payload.get("decision_rationale").and_then(|v| v.as_str()) {
                if s.len() > 16_384 {
                    return Err("policy_eval.payload.decision_rationale is too long".into());
                }
            }
            if let Some(s) = payload.get("explanation_summary").and_then(|v| v.as_str()) {
                if s.len() > 16_384 {
                    return Err("policy_eval.payload.explanation_summary is too long".into());
                }
            }
        }
        "human_gate" => {
            let appr = payload
                .get("approval_state")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            if !matches!(
                appr,
                "pending" | "approved" | "rejected" | "escalated" | "unknown"
            ) {
                return Err(
                    "human_gate.payload.approval_state must be pending|approved|rejected|escalated|unknown"
                        .into(),
                );
            }
            let ov = payload
                .get("override_state")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            if !matches!(ov, "none" | "applied" | "declined" | "pending") {
                return Err(
                    "human_gate.payload.override_state must be none|applied|declined|pending"
                        .into(),
                );
            }
            if matches!(appr, "approved" | "rejected") {
                let has_principal = payload
                    .get("approver_principal")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .trim()
                    .len()
                    > 0;
                let has_hash = payload
                    .get("approver_identity_hash")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .trim()
                    .len()
                    > 0;
                if !has_principal && !has_hash {
                    return Err(
                        "human_gate requires approver_principal or approver_identity_hash when approval_state is approved|rejected"
                            .into(),
                    );
                }
                let ts = payload
                    .get("approval_timestamp")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .trim();
                if ts.is_empty() {
                    return Err(
                        "human_gate requires approval_timestamp (RFC3339) when approval_state is approved|rejected"
                            .into(),
                    );
                }
                if DateTime::parse_from_rfc3339(ts).is_err() {
                    return Err("human_gate.payload.approval_timestamp must be RFC3339".into());
                }
            }
        }
        "completed" => {
            let v = payload
                .get("final_audit_verdict")
                .and_then(|x| x.as_str())
                .unwrap_or("");
            if !matches!(v, "VALID" | "INVALID" | "BLOCKED" | "UNKNOWN") {
                return Err(
                    "completed.payload.final_audit_verdict must be VALID|INVALID|BLOCKED|UNKNOWN"
                        .into(),
                );
            }
            json_string_array_ok(
                &payload.get("reason_codes").cloned().unwrap_or(json!([])),
                "reason_codes",
            )?;
            json_string_array_ok(
                &payload
                    .get("triggered_controls")
                    .cloned()
                    .unwrap_or(json!([])),
                "triggered_controls",
            )?;
            json_string_array_ok(
                &payload.get("evidence_refs").cloned().unwrap_or(json!([])),
                "evidence_refs",
            )?;
        }
        "approval_step" => {
            if payload
                .get("chain_index")
                .and_then(|v| v.as_i64())
                .is_none()
            {
                return Err("approval_step.payload.chain_index must be an integer".into());
            }
            let st = payload.get("state").and_then(|v| v.as_str()).unwrap_or("");
            if !matches!(st, "pending" | "approved" | "rejected" | "delegated") {
                return Err(
                    "approval_step.payload.state must be pending|approved|rejected|delegated"
                        .into(),
                );
            }
            if payload
                .get("principal")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim()
                .is_empty()
            {
                return Err("approval_step.payload.principal is required".into());
            }
        }
        "appeal" => {
            for k in ["appeal_id", "status", "summary"] {
                if payload
                    .get(k)
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .trim()
                    .is_empty()
                {
                    return Err(format!("appeal.payload.{k} is required"));
                }
            }
            let st = payload.get("status").and_then(|v| v.as_str()).unwrap_or("");
            if !matches!(
                st,
                "submitted" | "under_review" | "upheld" | "rejected" | "closed"
            ) {
                return Err(
                    "appeal.payload.status must be submitted|under_review|upheld|rejected|closed"
                        .into(),
                );
            }
        }
        "incident" => {
            for k in ["incident_id", "severity", "status", "summary"] {
                if payload
                    .get(k)
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .trim()
                    .is_empty()
                {
                    return Err(format!("incident.payload.{k} is required"));
                }
            }
            let sev = payload
                .get("severity")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            if !matches!(sev, "low" | "medium" | "high") {
                return Err("incident.payload.severity must be low|medium|high".into());
            }
            let st = payload.get("status").and_then(|v| v.as_str()).unwrap_or("");
            if !matches!(st, "open" | "mitigating" | "closed") {
                return Err("incident.payload.status must be open|mitigating|closed".into());
            }
        }
        "remediation" => {
            for k in [
                "remediation_id",
                "incident_id",
                "action_summary",
                "owner_principal",
                "status",
            ] {
                if payload
                    .get(k)
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .trim()
                    .is_empty()
                {
                    return Err(format!("remediation.payload.{k} is required"));
                }
            }
            let st = payload.get("status").and_then(|v| v.as_str()).unwrap_or("");
            if !matches!(st, "open" | "in_progress" | "closed") {
                return Err("remediation.payload.status must be open|in_progress|closed".into());
            }
        }
        "monitoring_sample" => {
            let k = payload
                .get("sample_kind")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            if !matches!(
                k,
                "latency"
                    | "cost"
                    | "drift"
                    | "override_rate"
                    | "incident_frequency"
                    | "control_failures"
            ) {
                return Err(
                    "monitoring_sample.payload.sample_kind must be latency|cost|drift|override_rate|incident_frequency|control_failures".into(),
                );
            }
            if !payload.get("metrics").is_some_and(|v| v.is_object()) {
                return Err("monitoring_sample.payload.metrics must be an object".into());
            }
        }
        "seal_attestation" => {
            let alg = payload
                .get("algorithm")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            if !matches!(alg, "sha256" | "sigstore" | "none") {
                return Err(
                    "seal_attestation.payload.algorithm must be sha256|sigstore|none".into(),
                );
            }
            if alg != "none"
                && payload
                    .get("digest")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .trim()
                    .is_empty()
            {
                return Err(
                    "seal_attestation.payload.digest is required unless algorithm is none".into(),
                );
            }
        }
        "legal_evidence_ref" => {
            for k in ["pack_kind", "ref_id"] {
                if payload
                    .get(k)
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .trim()
                    .is_empty()
                {
                    return Err(format!("legal_evidence_ref.payload.{k} is required"));
                }
            }
            let pk = payload
                .get("pack_kind")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            if !matches!(
                pk,
                "internal" | "external" | "regulator" | "customer" | "litigation"
            ) {
                return Err(
                    "legal_evidence_ref.payload.pack_kind must be internal|external|regulator|customer|litigation"
                        .into(),
                );
            }
        }
        "certification_mark" => {
            let fw = payload
                .get("framework")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            if !matches!(
                fw,
                "eu_ai_act" | "iso_42001" | "nist_ai_rmf" | "sector_specific"
            ) {
                return Err(
                    "certification_mark.payload.framework must be eu_ai_act|iso_42001|nist_ai_rmf|sector_specific"
                        .into(),
                );
            }
            let score = payload
                .get("readiness_score")
                .and_then(|v| v.as_i64())
                .unwrap_or(-1);
            if !(0..=100).contains(&score) {
                return Err("certification_mark.payload.readiness_score must be 0..=100".into());
            }
        }
        "business_impact" => {
            fn exposure_ok(v: &Value, name: &str) -> Result<(), String> {
                let n = v.get(name).and_then(|x| x.as_f64()).unwrap_or(-1.0);
                if !(0.0..=100.0).contains(&n) {
                    return Err(format!(
                        "business_impact.payload.{name} must be a number between 0 and 100"
                    ));
                }
                Ok(())
            }
            exposure_ok(payload, "regulatory_exposure")?;
            exposure_ok(payload, "legal_exposure")?;
            exposure_ok(payload, "financial_exposure")?;
            exposure_ok(payload, "reputational_exposure")?;
        }
        "executive_brief" => {
            if payload
                .get("headline")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim()
                .is_empty()
            {
                return Err("executive_brief.payload.headline is required".into());
            }
            let bullets = payload.get("bullets").cloned().unwrap_or(json!([]));
            let Some(arr) = bullets.as_array() else {
                return Err("executive_brief.payload.bullets must be an array".into());
            };
            if arr.len() > 20 {
                return Err("executive_brief.payload.bullets supports at most 20 entries".into());
            }
            for b in arr {
                if !b.is_string() {
                    return Err("executive_brief.payload.bullets entries must be strings".into());
                }
            }
        }
        other => return Err(format!("unsupported event_type: {other}")),
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn aggregate_single_agent_blocked() {
        let ev = vec![
            json!({
                "event_type": "trace_started",
                "payload": {
                    "model_provider": "openai",
                    "model_name": "gpt-4o",
                    "model_version": "2024-05-13",
                    "prompt_hash": "p1",
                    "input_hash": "i1",
                    "agent_id": "agent_root",
                    "agent_role": "planner",
                    "compliance_summary_run_id": "run-ledger-1"
                },
                "correlation_id": "corr-1",
                "created_at": "2026-01-01T00:00:00Z"
            }),
            json!({
                "event_type": "policy_eval",
                "payload": {
                    "policy_id": "pol_x",
                    "outcome": "block",
                    "reason_codes": ["DATA_RETENTION"]
                },
                "created_at": "2026-01-01T00:00:01Z"
            }),
            json!({
                "event_type": "completed",
                "payload": { "final_audit_verdict": "BLOCKED", "output_hash": "o1" },
                "created_at": "2026-01-01T00:00:02Z"
            }),
        ];
        let doc = aggregate_trace_export("tenant-a", "ai-run-1", &ev);
        assert_eq!(doc["trace_version"], json!(2));
        assert_eq!(doc["final_audit_verdict"], json!("BLOCKED"));
        assert_eq!(doc["policies_evaluated"][0]["outcome"], json!("block"));
        assert_eq!(doc["compliance_summary_run_id"], json!("run-ledger-1"));
        let v2 = doc.get("govai_functions_v2").expect("v2 block");
        assert_eq!(
            v2.get("schema_version").and_then(|x| x.as_str()),
            Some("aigov.functions_v2.extensions.v1")
        );
    }

    #[test]
    fn aggregate_delegation_chain() {
        let ev = vec![
            json!({
                "event_type": "trace_started",
                "payload": {
                    "model_provider": "anthropic",
                    "model_name": "claude-3-5-sonnet",
                    "prompt_hash": "p",
                    "input_hash": "i",
                    "agent_id": "lead",
                    "agent_role": "orchestrator"
                },
                "correlation_id": "c2",
                "created_at": "2026-01-02T00:00:00Z"
            }),
            json!({
                "event_type": "delegation",
                "payload": {
                    "parent_agent_id": "lead",
                    "child_agent_id": "worker",
                    "child_role": "executor"
                },
                "created_at": "2026-01-02T00:00:01Z"
            }),
            json!({
                "event_type": "tool_call",
                "payload": { "tool_name": "search", "input_hash": "t1", "output_hash": "t2" },
                "created_at": "2026-01-02T00:00:02Z"
            }),
            json!({
                "event_type": "human_gate",
                "payload": {
                    "approval_state": "approved",
                    "override_state": "none",
                    "approver_principal": "alice",
                    "approval_timestamp": "2026-01-02T00:00:03Z",
                    "approval_reason": "lgtm"
                },
                "created_at": "2026-01-02T00:00:03Z"
            }),
            json!({
                "event_type": "completed",
                "payload": { "final_audit_verdict": "VALID", "output_hash": "out" },
                "created_at": "2026-01-02T00:00:04Z"
            }),
        ];
        let doc = aggregate_trace_export("tenant-b", "ai-run-2", &ev);
        assert_eq!(doc["agents"]["delegations"].as_array().unwrap().len(), 1);
        assert_eq!(doc["human"]["approval_state"], json!("approved"));
        assert_eq!(doc["final_audit_verdict"], json!("VALID"));
    }

    #[test]
    fn validate_append_functions_v2_event_types() {
        assert!(validate_append_event(
            "approval_step",
            &json!({ "chain_index": 0, "state": "approved", "principal": "alice" })
        )
        .is_ok());
        assert!(validate_append_event(
            "business_impact",
            &json!({
                "regulatory_exposure": 1.0,
                "legal_exposure": 2.0,
                "financial_exposure": 3.0,
                "reputational_exposure": 4.0
            })
        )
        .is_ok());
        assert!(validate_append_event(
            "executive_brief",
            &json!({ "headline": "Q", "bullets": ["a", "b"] })
        )
        .is_ok());
    }
}
