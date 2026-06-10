//! Deterministic `aigov.audit_export.v1` document builder from ledger state.

use crate::bundle::{
    bundle_sha256, collect_events_for_run, find_model_artifact_path, portable_evidence_digest_v1,
};
use crate::compliance_summary::derive_verdict_from_state;
use crate::govai_environment::GovaiEnvironment;
use crate::policy_config::PolicyConfig;
use crate::governance_graph::{build_governance_graph, lineage_block_from_graph};
use crate::projection::derive_current_state_from_events_with_context;
use crate::schema::EvidenceEvent;
use serde_json::{json, Value};

pub fn build_audit_export_v1(
    run_id: &str,
    ledger_tenant_id: &str,
    log_path: &str,
    policy_version: &str,
    deployment_env: GovaiEnvironment,
    policy_cfg: &PolicyConfig,
) -> Result<Value, String> {
    let events = collect_events_for_run(log_path, run_id)?;
    if events.is_empty() {
        return Err("run_not_found".to_string());
    }

    let artifact = find_model_artifact_path(&events);
    let bundle_sha = bundle_sha256(
        run_id,
        policy_version,
        log_path,
        artifact.as_deref(),
        &events,
    );
    let events_content_sha256 = portable_evidence_digest_v1(run_id, &events);
    let exported_at = events.last().map(|e| e.ts_utc.clone());
    let state = derive_current_state_from_events_with_context(
        run_id,
        &events,
        Some(bundle_sha.clone()),
        exported_at.clone(),
    );
    let outcome = derive_verdict_from_state(&state, policy_cfg);

    let log_chain = build_log_chain(log_path, run_id)?;
    let chain_head = log_chain
        .last()
        .and_then(|e| e.get("record_hash"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    let discovery = discovery_section(&state);
    let discovery_findings = discovery_findings_from_events(&events);
    let human_approval = human_approval_json(&events);
    let promotion = promotion_json(&events);
    let timestamps = export_timestamps(&events);

    let identifiers = serde_json::to_value(&state.identifiers).unwrap_or(json!({}));
    let requirements = export_requirements(&state);
    let graph_doc = build_governance_graph(run_id, &events);
    let lineage = lineage_block_from_graph(&graph_doc);

    Ok(json!({
        "ok": true,
        "schema_version": "aigov.audit_export.v1",
        "policy_version": policy_version,
        "environment": deployment_env.as_str(),
        "exported_at_utc": exported_at,
        "tenant": {
            "ledger_tenant_id": ledger_tenant_id,
            "billing_tenant_id": ledger_tenant_id,
        },
        "run": {
            "run_id": run_id,
            "policy_version": policy_version,
            "log_path": log_path,
            "model_artifact_path": artifact,
            "identifiers": identifiers,
        },
        "discovery": discovery,
        "discovery_findings": discovery_findings,
        "evidence_hashes": {
            "bundle_sha256": bundle_sha,
            "events_content_sha256": events_content_sha256,
            "chain_head_record_sha256": chain_head,
            "log_chain": log_chain,
        },
        "decision": {
            "human_approval": human_approval,
            "promotion": promotion,
            "evaluation_passed": state.model.evaluation_passed,
            "verdict": outcome.verdict,
            "blocked_reasons": outcome.blocked_reasons,
            "reason_codes": outcome.reason_codes,
        },
        "evidence_requirements": requirements,
        "evidence_events": events,
        "timestamps": timestamps,
        "lineage": lineage,
    }))
}

fn build_log_chain(log_path: &str, run_id: &str) -> Result<Vec<Value>, String> {
    let (records, _) = crate::audit_store::scan_ledger_records(log_path)?;
    let mut chain: Vec<Value> = Vec::new();
    for rec in records {
        let ev: EvidenceEvent =
            serde_json::from_str(&rec.event_json).map_err(|e| e.to_string())?;
        if ev.run_id != run_id {
            continue;
        }
        chain.push(json!({
            "event_id": ev.event_id,
            "ts_utc": ev.ts_utc,
            "event_type": ev.event_type,
            "prev_hash": rec.prev_hash,
            "record_hash": rec.record_hash,
        }));
    }
    chain.sort_by(|a, b| {
        let ta = a.get("ts_utc").and_then(|v| v.as_str()).unwrap_or("");
        let tb = b.get("ts_utc").and_then(|v| v.as_str()).unwrap_or("");
        ta.cmp(tb).then_with(|| {
            let ea = a.get("event_id").and_then(|v| v.as_str()).unwrap_or("");
            let eb = b.get("event_id").and_then(|v| v.as_str()).unwrap_or("");
            ea.cmp(eb)
        })
    });
    Ok(chain)
}

fn discovery_section(state: &crate::projection::ComplianceCurrentState) -> Value {
    json!({
        "findings": {
            "openai": state.discovery.openai,
            "transformers": state.discovery.transformers,
            "model_artifacts": state.discovery.model_artifacts,
        },
        "required_evidence": state.requirements.required,
        "required_requirements": state.requirements.required_requirements,
    })
}

fn discovery_findings_from_events(events: &[EvidenceEvent]) -> Vec<Value> {
    let mut out: Vec<Value> = Vec::new();
    for e in events.iter().rev() {
        if e.event_type != "ai_discovery_reported" {
            continue;
        }
        if let Some(arr) = e.payload.get("findings").and_then(|v| v.as_array()) {
            for item in arr {
                if item.is_object() {
                    out.push(item.clone());
                }
            }
        }
        break;
    }
    out.sort_by(|a, b| {
        let pa = a.get("file_path").and_then(|v| v.as_str()).unwrap_or("");
        let pb = b.get("file_path").and_then(|v| v.as_str()).unwrap_or("");
        pa.cmp(pb)
    });
    out
}

fn export_requirements(state: &crate::projection::ComplianceCurrentState) -> Value {
    json!({
        "required_evidence": state.requirements.required,
        "provided_evidence": state.requirements.satisfied,
        "missing_evidence": state.requirements.missing,
        "required_requirements": state.requirements.required_requirements,
        "provided_requirements": state.requirements.satisfied_requirements,
        "missing_requirements": state.requirements.missing_requirements,
    })
}

fn human_approval_json(events: &[EvidenceEvent]) -> Value {
    for e in events.iter().rev() {
        if e.event_type != "human_approved" {
            continue;
        }
        return json!({
            "approval_event_id": e.event_id,
            "ts_utc": e.ts_utc,
            "scope": e.payload.get("scope"),
            "decision": e.payload.get("decision"),
            "approver": e.payload.get("approver"),
        });
    }
    Value::Null
}

fn promotion_json(events: &[EvidenceEvent]) -> Value {
    for e in events.iter().rev() {
        if e.event_type != "model_promoted" {
            continue;
        }
        return json!({
            "promotion_event_id": e.event_id,
            "ts_utc": e.ts_utc,
            "artifact_path": e.payload.get("artifact_path"),
            "artifact_sha256": e.payload.get("artifact_sha256"),
        });
    }
    Value::Null
}

fn export_timestamps(events: &[EvidenceEvent]) -> Value {
    let first = events.first().map(|e| e.ts_utc.clone());
    let last = events.last().map(|e| e.ts_utc.clone());
    let human = events
        .iter()
        .rev()
        .find(|e| e.event_type == "human_approved")
        .map(|e| e.ts_utc.clone());
    let promotion = events
        .iter()
        .rev()
        .find(|e| e.event_type == "model_promoted")
        .map(|e| e.ts_utc.clone());
    json!({
        "first_event_ts_utc": first,
        "last_event_ts_utc": last,
        "human_approval_ts_utc": human,
        "promotion_ts_utc": promotion,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::audit_store::append_record_atomic_with_run_count;
    use crate::schema::EvidenceEvent;
    use tempfile::TempDir;

    fn write_minimal_valid_run(_dir: &std::path::Path, tenant: &str, run_id: &str) -> String {
        let log_path = crate::project::resolve_ledger_path("audit_log.jsonl", tenant);
        let _ = std::fs::create_dir_all(
            std::path::Path::new(&log_path)
                .parent()
                .unwrap_or(std::path::Path::new(".")),
        );
        let events = vec![
            EvidenceEvent {
                event_id: format!("{run_id}-disc"),
                event_type: "ai_discovery_reported".to_string(),
                ts_utc: "2026-01-01T00:00:01Z".to_string(),
                actor: "t".to_string(),
                system: "t".to_string(),
                run_id: run_id.to_string(),
                environment: None,
                payload: json!({"openai": false, "transformers": false, "model_artifacts": false}),
                parent_run_id: None,
                root_run_id: None,
                delegated_from_event_id: None,
                agent_id: None,
                agent_role: None,
                delegation_reason: None,
            },
        ];
        for e in events {
            append_record_atomic_with_run_count(&log_path, e).expect("append");
        }
        log_path
    }

    #[test]
    fn export_schema_version_and_hashes() {
        let tmp = TempDir::new().unwrap();
        std::env::set_var("GOVAI_LEDGER_DIR", tmp.path());
        let run_id = "export-run-1";
        let log_path = write_minimal_valid_run(tmp.path(), "tenant-x", run_id);
        let doc = build_audit_export_v1(
            run_id,
            "tenant-x",
            &log_path,
            "test-policy",
            GovaiEnvironment::Dev,
            &PolicyConfig::default(),
        )
        .expect("export");
        assert_eq!(
            doc.get("schema_version").and_then(|v| v.as_str()),
            Some("aigov.audit_export.v1")
        );
        let hashes = doc.get("evidence_hashes").expect("hashes");
        assert!(hashes.get("bundle_sha256").is_some());
        assert!(hashes.get("events_content_sha256").is_some());
    }
}
