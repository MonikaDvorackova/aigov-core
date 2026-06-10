//! Deterministic governance replay from ``aigov.audit_export.v1`` documents.

use crate::policy_config::PolicyConfig;
use crate::replay_projection::{project_governance_state, ReplayProjection};
use crate::governance_graph::build_governance_graph;
use crate::replay_validation::{
    events_for_projection, export_run_id, run_export_validations, ReplayValidationReport,
};
use crate::schema::EvidenceEvent;
use serde::Serialize;
use serde_json::Value;
use sha2::{Digest, Sha256};

#[derive(Debug, Serialize)]
pub struct ReplayIntegrityStatus {
    pub replay_integrity: String,
    pub replay_consistency: String,
    pub verdict_match: bool,
}

#[derive(Debug, Serialize)]
pub struct ReplayResult {
    pub ok: bool,
    pub schema_version: String,
    pub run_id: String,
    pub event_count: usize,
    pub exported_verdict: Option<String>,
    pub reconstructed_verdict: String,
    pub integrity: ReplayIntegrityStatus,
    pub validation: ReplayValidationReport,
    pub projection: Option<ReplayProjection>,
    pub determinism_digest: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub lineage: Option<Value>,
}

pub fn replay_audit_export_v1(export: &Value, policy_cfg: &PolicyConfig) -> ReplayResult {
    let (mut validation, events) = run_export_validations(export);
    let run_id = export_run_id(export).unwrap_or_default();
    let schema_version = export
        .get("schema_version")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let exported_verdict = export
        .get("decision")
        .and_then(|d| d.get("verdict"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    if run_id.is_empty() || events.is_empty() || !validation.is_ok() {
        return ReplayResult {
            ok: false,
            schema_version,
            run_id,
            event_count: events.len(),
            exported_verdict,
            reconstructed_verdict: String::new(),
            integrity: ReplayIntegrityStatus {
                replay_integrity: "failed".to_string(),
                replay_consistency: "failed".to_string(),
                verdict_match: false,
            },
            validation,
            projection: None,
            determinism_digest: String::new(),
            lineage: None,
        };
    }

    let lineage_doc = build_governance_graph(&run_id, &events);
    let lineage = serde_json::to_value(&lineage_doc.summary).ok();

    let projection_events = events_for_projection(&events);
    let bundle_sha = export
        .get("evidence_hashes")
        .and_then(|h| h.get("bundle_sha256"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let exported_at = export
        .get("exported_at_utc")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    let projection = project_governance_state(
        &run_id,
        &projection_events,
        bundle_sha,
        exported_at,
        policy_cfg,
    );
    let reconstructed_verdict = projection.outcome.verdict.clone();
    let verdict_match = exported_verdict.as_deref() == Some(reconstructed_verdict.as_str());

    if !verdict_match {
        validation.push_error(
            "verdict_mismatch",
            format!(
                "export decision.verdict {:?} != replayed {:?}",
                exported_verdict, reconstructed_verdict
            ),
        );
    }

    let determinism_digest = replay_determinism_digest(&run_id, &projection_events, policy_cfg);

    let replay_integrity = if validation.chain_continuity_ok
        && validation.events_content_sha256_ok
        && validation.run_id_consistent
    {
        "ok"
    } else {
        "degraded"
    };

    let replay_consistency = if validation.is_ok() && validation.event_ordering_ok && verdict_match {
        "ok"
    } else {
        "failed"
    };

    let ok = validation.is_ok() && verdict_match;

    ReplayResult {
        ok,
        schema_version,
        run_id,
        event_count: events.len(),
        exported_verdict,
        reconstructed_verdict,
        integrity: ReplayIntegrityStatus {
            replay_integrity: replay_integrity.to_string(),
            replay_consistency: replay_consistency.to_string(),
            verdict_match,
        },
        validation,
        projection: Some(projection),
        determinism_digest,
        lineage,
    }
}

/// Stable digest of replay outputs for cross-run determinism checks.
pub fn replay_determinism_digest(
    run_id: &str,
    events: &[EvidenceEvent],
    policy_cfg: &PolicyConfig,
) -> String {
    let projection = project_governance_state(run_id, events, None, None, policy_cfg);
    let payload = serde_json::json!({
        "run_id": run_id,
        "verdict": projection.outcome.verdict,
        "reason_codes": projection.outcome.reason_codes,
        "promotion_state": projection.current_state.model.promotion.state,
        "evaluation_passed": projection.current_state.model.evaluation_passed,
        "missing_evidence": projection.current_state.requirements.missing,
    });
    let bytes = serde_json::to_vec(&payload).expect("replay digest json");
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

pub fn replay_audit_export_json(
    export_json: &str,
    policy_cfg: &PolicyConfig,
) -> Result<ReplayResult, String> {
    let export: Value =
        serde_json::from_str(export_json).map_err(|e| format!("parse export json: {e}"))?;
    Ok(replay_audit_export_v1(&export, policy_cfg))
}

pub fn replay_result_to_json(result: &ReplayResult) -> Value {
    serde_json::to_value(result).expect("ReplayResult serializes")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::replay_validation::EXPORT_SCHEMA_V1;
    use serde_json::json;

    fn discovery(run_id: &str, id: &str) -> Value {
        json!({
            "event_id": id,
            "event_type": "ai_discovery_reported",
            "ts_utc": "2026-01-01T00:00:01Z",
            "actor": "t",
            "system": "t",
            "run_id": run_id,
            "payload": { "openai": false, "transformers": false, "model_artifacts": false }
        })
    }

    fn build_export(run_id: &str, events: Vec<Value>, verdict: &str, chain: Vec<Value>) -> Value {
        let parsed: Vec<EvidenceEvent> = events
            .iter()
            .map(|e| serde_json::from_value(e.clone()).unwrap())
            .collect();
        let ordered = events_for_projection(&parsed);
        let events_sha = crate::bundle::portable_evidence_digest_v1(run_id, &ordered);
        let mut evs = events;
        evs.sort_by(|a, b| {
            let ta = a.get("ts_utc").and_then(|v| v.as_str()).unwrap_or("");
            let tb = b.get("ts_utc").and_then(|v| v.as_str()).unwrap_or("");
            ta.cmp(tb)
        });
        json!({
            "ok": true,
            "schema_version": EXPORT_SCHEMA_V1,
            "policy_version": "test",
            "environment": "dev",
            "exported_at_utc": "2026-01-01T00:00:07Z",
            "run": { "run_id": run_id, "policy_version": "test", "log_path": "l.jsonl", "identifiers": {} },
            "evidence_hashes": {
                "bundle_sha256": "c".repeat(64),
                "events_content_sha256": events_sha,
                "log_chain": chain,
            },
            "decision": { "verdict": verdict, "blocked_reasons": [], "evaluation_passed": null },
            "evidence_events": evs,
        })
    }

    fn golden_events(run_id: &str) -> Vec<Value> {
        vec![
            discovery(run_id, &format!("{run_id}-disc")),
            json!({
                "event_id": format!("{run_id}-data"),
                "event_type": "data_registered",
                "ts_utc": "2026-01-01T00:00:02Z",
                "actor": "t", "system": "t", "run_id": run_id,
                "payload": {
                    "ai_system_id": "as1", "dataset_id": "ds1", "dataset": "ds",
                    "dataset_version": "v1", "dataset_fingerprint": "fp",
                    "dataset_governance_id": "dg1", "dataset_governance_commitment": "basic",
                    "source": "internal", "intended_use": "test", "limitations": "none",
                    "quality_summary": "ok", "governance_status": "registered"
                }
            }),
            json!({
                "event_id": format!("{run_id}-train"),
                "event_type": "model_trained",
                "ts_utc": "2026-01-01T00:00:02Z",
                "actor": "t", "system": "t", "run_id": run_id,
                "payload": {
                    "model_version_id": "mv1", "ai_system_id": "as1", "dataset_id": "ds1",
                    "model_type": "test",
                    "artifact_path": "registry://test/m",
                    "artifact_sha256": "abc1234567890123456789012345678901234567890123456789012345678901234"
                }
            }),
            json!({
                "event_id": format!("{run_id}-eval"),
                "event_type": "evaluation_reported",
                "ts_utc": "2026-01-01T00:00:03Z",
                "actor": "t", "system": "t", "run_id": run_id,
                "payload": {
                    "ai_system_id": "as1", "dataset_id": "ds1", "model_version_id": "mv1",
                    "metric": "accuracy", "value": 0.95, "threshold": 0.8, "passed": true
                }
            }),
            json!({
                "event_id": format!("{run_id}-risk"),
                "event_type": "risk_recorded",
                "ts_utc": "2026-01-01T00:00:04Z",
                "actor": "t", "system": "t", "run_id": run_id,
                "payload": {
                    "assessment_id": "a1", "ai_system_id": "as1", "dataset_id": "ds1",
                    "model_version_id": "mv1", "risk_id": "r1", "risk_class": "high",
                    "severity": 4.0, "likelihood": 0.3, "status": "submitted",
                    "mitigation": "m", "owner": "o", "dataset_governance_commitment": "basic"
                }
            }),
            json!({
                "event_id": format!("{run_id}-review"),
                "event_type": "risk_reviewed",
                "ts_utc": "2026-01-01T00:00:05Z",
                "actor": "t", "system": "t", "run_id": run_id,
                "payload": {
                    "assessment_id": "a1", "ai_system_id": "as1", "dataset_id": "ds1",
                    "model_version_id": "mv1", "risk_id": "r1", "decision": "approve",
                    "reviewer": "officer", "justification": "ok",
                    "dataset_governance_commitment": "basic"
                }
            }),
            json!({
                "event_id": format!("{run_id}-human"),
                "event_type": "human_approved",
                "ts_utc": "2026-01-01T00:00:06Z",
                "actor": "t", "system": "t", "run_id": run_id,
                "payload": {
                    "scope": "model_promoted", "decision": "approve", "approver": "officer",
                    "justification": "ok", "assessment_id": "a1", "risk_id": "r1",
                    "dataset_governance_commitment": "basic",
                    "ai_system_id": "as1", "dataset_id": "ds1", "model_version_id": "mv1"
                }
            }),
            json!({
                "event_id": format!("{run_id}-promote"),
                "event_type": "model_promoted",
                "ts_utc": "2026-01-01T00:00:07Z",
                "actor": "t", "system": "t", "run_id": run_id,
                "payload": {
                    "ai_system_id": "as1", "dataset_id": "ds1", "model_version_id": "mv1",
                    "artifact_path": "registry://test/m",
                    "artifact_sha256": "abc1234567890123456789012345678901234567890123456789012345678901234",
                    "promotion_reason": "test",
                    "approved_human_event_id": format!("{run_id}-human"),
                    "assessment_id": "a1", "risk_id": "r1",
                    "dataset_governance_commitment": "basic"
                }
            }),
        ]
    }

    fn chain_for(events: &[Value]) -> Vec<Value> {
        let mut prev: Option<String> = None;
        let mut out = Vec::new();
        for (i, ev) in events.iter().enumerate() {
            let rh = format!("{:064x}", i + 1);
            out.push(json!({
                "event_id": ev.get("event_id").and_then(|v| v.as_str()).unwrap_or(""),
                "ts_utc": ev.get("ts_utc").and_then(|v| v.as_str()).unwrap_or(""),
                "event_type": ev.get("event_type").and_then(|v| v.as_str()).unwrap_or(""),
                "prev_hash": prev,
                "record_hash": rh,
            }));
            prev = Some(rh);
        }
        out
    }

    #[test]
    fn stable_replay_valid_verdict() {
        let run_id = "replay-valid";
        let events = golden_events(run_id);
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "VALID", chain);
        let r1 = replay_audit_export_v1(&export, &PolicyConfig::default());
        let r2 = replay_audit_export_v1(&export, &PolicyConfig::default());
        assert!(r1.ok);
        assert_eq!(r1.reconstructed_verdict, "VALID");
        assert!(r1.integrity.verdict_match);
        assert_eq!(r1.determinism_digest, r2.determinism_digest);
    }

    #[test]
    fn reordered_event_detection() {
        let run_id = "replay-reorder";
        let mut events = golden_events(run_id);
        if events.len() >= 2 {
            events.swap(1, 2);
        }
        let chain = chain_for(&golden_events(run_id));
        let export = build_export(run_id, events, "VALID", chain);
        let r = replay_audit_export_v1(&export, &PolicyConfig::default());
        assert!(!r.validation.event_ordering_ok);
    }

    #[test]
    fn missing_approval_blocks_valid() {
        let run_id = "replay-no-approval";
        let events: Vec<Value> = golden_events(run_id)
            .into_iter()
            .filter(|e| {
                let et = e.get("event_type").and_then(|v| v.as_str()).unwrap_or("");
                et != "human_approved" && et != "model_promoted"
            })
            .collect();
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "BLOCKED", chain);
        let r = replay_audit_export_v1(&export, &PolicyConfig::default());
        assert_eq!(r.reconstructed_verdict, "BLOCKED");
        let expl = &r.projection.as_ref().expect("projection").explanation;
        assert!(expl.why_blocked.iter().any(|s| s.contains("approval") || s.contains("Promotion")));
    }

    #[test]
    fn chain_break_detection() {
        let run_id = "replay-chain";
        let events = golden_events(run_id);
        let mut chain = chain_for(&events);
        if chain.len() > 1 {
            chain[1]["prev_hash"] = json!("deadbeef");
        }
        let export = build_export(run_id, events, "BLOCKED", chain);
        let r = replay_audit_export_v1(&export, &PolicyConfig::default());
        assert!(!r.validation.chain_continuity_ok);
    }

    #[test]
    fn verdict_mismatch_detection() {
        let run_id = "replay-mismatch";
        let events: Vec<Value> = golden_events(run_id)
            .into_iter()
            .filter(|e| {
                let et = e.get("event_type").and_then(|v| v.as_str()).unwrap_or("");
                et != "human_approved" && et != "model_promoted"
            })
            .collect();
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "VALID", chain);
        let r = replay_audit_export_v1(&export, &PolicyConfig::default());
        assert_eq!(r.reconstructed_verdict, "BLOCKED");
        assert!(!r.integrity.verdict_match);
        assert!(r.validation.errors.iter().any(|e| e.code == "verdict_mismatch"));
    }

    #[test]
    fn duplicate_event_ids_fail() {
        let run_id = "replay-dup";
        let mut events = golden_events(run_id);
        events.push(events[0].clone());
        let chain = chain_for(&events);
        let export = build_export(run_id, events, "BLOCKED", chain);
        let r = replay_audit_export_v1(&export, &PolicyConfig::default());
        assert!(!r.validation.duplicate_event_ids.is_empty());
    }
}
