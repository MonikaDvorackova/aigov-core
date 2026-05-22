//! GovAI Functions 2.0 — decision intelligence and governance operating system HTTP surface.
//!
//! Responses are derived from append-only AI decision trace events. The immutable ledger verdict
//! for a run remains authoritative only from [`GET /compliance-summary`](crate::govai_api).

use std::collections::BTreeSet;

use axum::extract::{Path, State};
use axum::http::{HeaderMap, StatusCode};
use axum::routing::get;
use axum::{Json, Router};
use serde_json::{json, Value};

use crate::ai_decision_audit::aggregate_trace_export;
use crate::ai_decision_http::read_trace_events_bundle;
use crate::db::DbPool;
use crate::govai_api::AppState;

const FLIGHT_PACK_SCHEMA: &str = "aigov.govai_functions_v2.flight_pack.v1";

pub fn summarize_monitoring_samples(samples: Option<&Value>) -> Value {
    let Some(Value::Array(arr)) = samples else {
        return json!({"samples": 0, "kinds_observed": []});
    };
    let mut kinds = BTreeSet::new();
    for s in arr {
        if let Some(k) = s.get("sample_kind").and_then(|x| x.as_str()) {
            kinds.insert(k.to_string());
        }
    }
    json!({
        "samples": arr.len(),
        "kinds_observed": kinds.into_iter().collect::<Vec<_>>(),
    })
}

pub fn governance_scorecard_deterministic(base: &Value, events: &[Value]) -> Value {
    let integrity_ok = base
        .get("trace_integrity")
        .and_then(|t| t.get("status"))
        .and_then(|s| s.as_str())
        == Some("ok");
    let consistent = base.get("verdict_consistent").and_then(|v| v.as_bool()) == Some(true);
    let n_pol = base
        .get("policies_evaluated")
        .and_then(|p| p.as_array())
        .map(|a| a.len())
        .unwrap_or(0);
    let v2 = base.get("govai_functions_v2");
    let has_seal = v2
        .and_then(|v| v.get("seal_attestations"))
        .and_then(|x| x.as_array())
        .map(|a| !a.is_empty())
        .unwrap_or(false);
    let has_legal = v2
        .and_then(|v| v.get("legal_evidence_refs"))
        .and_then(|x| x.as_array())
        .map(|a| !a.is_empty())
        .unwrap_or(false);
    let n_ap = v2
        .and_then(|v| v.get("approval_steps"))
        .and_then(|x| x.as_array())
        .map(|a| a.len())
        .unwrap_or(0);
    let mut s: i64 = 35;
    if integrity_ok {
        s += 25;
    }
    if consistent {
        s += 15;
    }
    s += (n_pol.min(6) as i64) * 4;
    if n_ap >= 2 {
        s += 10;
    }
    if has_seal {
        s += 5;
    }
    if has_legal {
        s += 5;
    }
    let tool_calls = events
        .iter()
        .filter(|e| e.get("event_type").and_then(|x| x.as_str()) == Some("tool_call"))
        .count() as i64;
    if tool_calls > 0 {
        s += 3;
    }
    s = s.clamp(0, 100);
    json!({
        "governance_readiness_0_100": s,
        "integrity_ok": integrity_ok,
        "verdict_consistent": consistent,
        "policies_evaluated_count": n_pol,
        "approval_steps_count": n_ap,
        "seal_present": has_seal,
        "legal_evidence_refs_present": has_legal,
        "tool_call_events": tool_calls,
    })
}

pub fn governance_operating_system_view(base: &Value, events: &[Value]) -> Value {
    let v2 = base.get("govai_functions_v2").cloned().unwrap_or(json!({}));
    let wf = json!({
        "approval_steps_recorded": v2.get("approval_steps").and_then(|x| x.as_array()).map(|a| a.len()).unwrap_or(0),
        "appeals_recorded": v2.get("appeals").and_then(|x| x.as_array()).map(|a| a.len()).unwrap_or(0),
        "incidents_recorded": v2.get("incidents").and_then(|x| x.as_array()).map(|a| a.len()).unwrap_or(0),
        "remediations_recorded": v2.get("remediations").and_then(|x| x.as_array()).map(|a| a.len()).unwrap_or(0),
        "certification_marks_recorded": v2.get("certification_marks").and_then(|x| x.as_array()).map(|a| a.len()).unwrap_or(0),
    });
    json!({
        "workflow_counts": wf,
        "governance_scorecard": governance_scorecard_deterministic(base, events),
        "continuous_monitoring": summarize_monitoring_samples(v2.get("monitoring_samples")),
    })
}

pub fn build_flight_pack_document(ledger_tenant_id: &str, run_id: &str, events: &[Value]) -> Value {
    let base = aggregate_trace_export(ledger_tenant_id, run_id, events);
    let gos = governance_operating_system_view(&base, events);
    json!({
        "ok": true,
        "schema_version": FLIGHT_PACK_SCHEMA,
        "flight_pack_version": 1,
        "ledger_tenant_id": ledger_tenant_id,
        "run_id": run_id,
        "base_export": base,
        "governance_operating_system": gos,
    })
}

fn last_executive_brief(events: &[Value]) -> Option<Value> {
    for e in events.iter().rev() {
        if e.get("event_type").and_then(|x| x.as_str()) == Some("executive_brief") {
            return Some(e.get("payload").cloned().unwrap_or(json!({})));
        }
    }
    None
}

pub fn executive_summary_document(base: &Value, events: &[Value]) -> Value {
    json!({
        "ok": true,
        "schema_version": "aigov.govai_functions_v2.executive_summary.v1",
        "run_id": base.get("run_id"),
        "ledger_tenant_id": base.get("ledger_tenant_id"),
        "model": base.get("model"),
        "final_audit_verdict": base.get("final_audit_verdict"),
        "derived_audit_verdict": base.get("derived_audit_verdict"),
        "trace_integrity": base.get("trace_integrity"),
        "executive_brief": last_executive_brief(events),
        "governance_scorecard": governance_scorecard_deterministic(base, events),
    })
}

pub fn legal_evidence_manifest_document(base: &Value) -> Value {
    let refs = base
        .get("govai_functions_v2")
        .and_then(|v| v.get("legal_evidence_refs"))
        .cloned()
        .unwrap_or(json!([]));
    json!({
        "ok": true,
        "schema_version": "aigov.govai_functions_v2.legal_evidence_manifest.v1",
        "run_id": base.get("run_id"),
        "ledger_tenant_id": base.get("ledger_tenant_id"),
        "legal_evidence_refs": refs,
        "relation_to_compliance_summary": "Pack manifests index operational legal-evidence references from the flight recorder. Authoritative ledger exports use GET /api/export/:run_id and GET /compliance-summary.",
    })
}

async fn get_flight_pack(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(run_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    match read_trace_events_bundle(&state.pool, &headers, &run_id).await {
        Ok((ledger_tid, rid, events)) => (
            StatusCode::OK,
            Json(build_flight_pack_document(&ledger_tid, &rid, &events)),
        ),
        Err(r) => r,
    }
}

async fn get_executive_summary(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(run_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    match read_trace_events_bundle(&state.pool, &headers, &run_id).await {
        Ok((ledger_tid, rid, events)) => {
            let base = aggregate_trace_export(&ledger_tid, &rid, &events);
            (
                StatusCode::OK,
                Json(executive_summary_document(&base, &events)),
            )
        }
        Err(r) => r,
    }
}

async fn get_legal_manifest(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(run_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    match read_trace_events_bundle(&state.pool, &headers, &run_id).await {
        Ok((ledger_tid, rid, events)) => {
            let base = aggregate_trace_export(&ledger_tid, &rid, &events);
            (
                StatusCode::OK,
                Json(legal_evidence_manifest_document(&base)),
            )
        }
        Err(r) => r,
    }
}

async fn get_governance_scorecard(
    State(state): State<AppState>,
    headers: HeaderMap,
    Path(run_id): Path<String>,
) -> (StatusCode, Json<Value>) {
    match read_trace_events_bundle(&state.pool, &headers, &run_id).await {
        Ok((ledger_tid, rid, events)) => {
            let base = aggregate_trace_export(&ledger_tid, &rid, &events);
            (
                StatusCode::OK,
                Json(json!({
                    "ok": true,
                    "schema_version": "aigov.govai_functions_v2.governance_scorecard.v1",
                    "run_id": rid,
                    "ledger_tenant_id": ledger_tid,
                    "governance_scorecard": governance_scorecard_deterministic(&base, &events),
                })),
            )
        }
        Err(r) => r,
    }
}

pub fn router(pool: DbPool) -> Router {
    let state = AppState { pool };
    Router::new()
        .route(
            "/api/functions/v2/:run_id/flight-pack",
            get(get_flight_pack),
        )
        .route(
            "/api/functions/v2/:run_id/executive-summary",
            get(get_executive_summary),
        )
        .route(
            "/api/functions/v2/:run_id/legal-evidence-manifest",
            get(get_legal_manifest),
        )
        .route(
            "/api/functions/v2/:run_id/governance-scorecard",
            get(get_governance_scorecard),
        )
        .with_state(state)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn scorecard_bounds_and_manifest_shape() {
        let events = vec![
            json!({"event_type": "trace_started", "payload": {
                "model_provider": "openai", "model_name": "gpt-4o", "prompt_hash": "p", "input_hash": "i",
                "agent_id": "a1", "agent_role": "r"
            }}),
            json!({"event_type": "policy_eval", "payload": {"policy_id": "pol", "outcome": "allow"}}),
            json!({"event_type": "completed", "payload": {"final_audit_verdict": "VALID"}}),
        ];
        let base = aggregate_trace_export("t1", "r1", &events);
        let sc = governance_scorecard_deterministic(&base, &events);
        let n = sc
            .get("governance_readiness_0_100")
            .and_then(|v| v.as_i64())
            .unwrap();
        assert!((0..=100).contains(&n));
        let m = legal_evidence_manifest_document(&base);
        assert_eq!(
            m.get("schema_version").and_then(|v| v.as_str()),
            Some("aigov.govai_functions_v2.legal_evidence_manifest.v1")
        );
    }
}
