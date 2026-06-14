use crate::schema::EvidenceEvent;
use serde::Serialize;
use serde_json::Value;
use std::collections::BTreeMap;
use std::collections::BTreeSet;

fn payload_get_str(p: &Value, key: &str) -> Option<String> {
    p.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
}

fn payload_get_num(p: &Value, key: &str) -> Option<f64> {
    p.get(key).and_then(|v| v.as_f64())
}

fn payload_get_bool(p: &Value, key: &str) -> Option<bool> {
    p.get(key).and_then(|v| v.as_bool())
}

fn find_last_event<'a>(events: &'a [EvidenceEvent], event_type: &str) -> Option<&'a EvidenceEvent> {
    events.iter().rev().find(|e| e.event_type == event_type)
}

fn find_last_payload_str_for_event_types(
    events: &[EvidenceEvent],
    event_types: &[&str],
    key: &str,
) -> Option<String> {
    events
        .iter()
        .rev()
        .find(|e| event_types.contains(&e.event_type.as_str()))
        .and_then(|e| payload_get_str(&e.payload, key))
}

fn find_last_event_by_scope<'a>(
    events: &'a [EvidenceEvent],
    event_type: &str,
    scope: &str,
) -> Option<&'a EvidenceEvent> {
    events.iter().rev().find(|e| {
        e.event_type == event_type && payload_get_str(&e.payload, "scope").as_deref() == Some(scope)
    })
}

#[derive(Debug, Serialize)]
pub struct RiskReviewSummary {
    pub decision: Option<String>,
    pub reviewer: Option<String>,
    pub justification: Option<String>,
    pub ts_utc: Option<String>,
    pub risk_review_event_id: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct RiskRecordSummary {
    pub risk_id: String,
    pub ai_system_id: Option<String>,
    pub dataset_id: Option<String>,
    pub model_version_id: Option<String>,
    pub risk_class: Option<String>,
    pub severity: Option<f64>,
    pub likelihood: Option<f64>,
    pub status: Option<String>,
    pub mitigation: Option<String>,
    pub owner: Option<String>,
    pub latest_review: Option<RiskReviewSummary>,
}

#[derive(Debug, Serialize)]
pub struct RiskSummary {
    pub total_risks: usize,
    pub by_risk_class: BTreeMap<String, usize>,
    pub risks: Vec<RiskRecordSummary>,
}

#[derive(Debug, Serialize)]
pub struct PromotionState {
    pub state: String,
    pub reason: Option<String>,
    pub model_promoted_present: bool,
}

#[derive(Debug, Serialize)]
pub struct DatasetGovernanceSummary {
    pub dataset_id: Option<String>,
    pub dataset_governance_id: Option<String>,
    pub dataset_governance_version: Option<String>,
    pub dataset_fingerprint: Option<String>,
    pub dataset_governance_commitment: Option<String>,
    pub governance_status: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct CanonicalIdentifiers {
    pub ai_system_id: Option<String>,
    pub dataset_id: Option<String>,
    pub model_version_id: Option<String>,
    pub primary_risk_id: Option<String>,
    pub risk_ids: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct SystemIdentityState {
    pub ai_system_id: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct ModelIdentityState {
    pub model_version_id: Option<String>,
    pub evaluation_passed: Option<bool>,
    pub promotion: PromotionState,
}

#[derive(Debug, Serialize)]
pub struct ApprovalState {
    pub scope: Option<String>,
    pub approver: Option<String>,
    pub approved_at: Option<String>,
    pub risk_review_decision: Option<String>,
    pub human_approval_decision: Option<String>,
    pub approved_human_event_id: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct EvidenceState {
    pub events_total: usize,
    pub latest_event_ts_utc: Option<String>,
    pub bundle_hash: Option<String>,
    pub bundle_generated_at: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct DiscoverySignals {
    pub openai: bool,
    pub transformers: bool,
    pub model_artifacts: bool,
}

#[derive(Debug, Serialize, Clone)]
pub struct Requirement {
    pub code: String,
    /// One of: `policy`, `discovery`, `lifecycle`.
    pub source: String,
    pub description: String,
}

fn requirement_source_and_description(code: &str) -> (&'static str, &'static str) {
    match code {
        // Lifecycle gates
        "ai_discovery_completed" => (
            "lifecycle",
            "AI discovery scan must be completed before compliance decision.",
        ),

        // Discovery-driven requirements
        "model_registered" => (
            "discovery",
            "Detected OpenAI usage requires model registration.",
        ),
        "usage_policy_defined" => (
            "discovery",
            "Detected OpenAI usage requires usage policy definition.",
        ),
        "evaluation_completed" => (
            "discovery",
            "Detected AI system requires evaluation evidence.",
        ),
        "model_artifact_documented" => (
            "discovery",
            "Detected model artifact requires documentation.",
        ),

        // Defensive fallback: still deterministic, but marks unknown requirements as policy-derived.
        _ => ("policy", "Policy requirement."),
    }
}

fn to_requirement(code: &str) -> Requirement {
    let (source, description) = requirement_source_and_description(code);
    Requirement {
        code: code.to_string(),
        source: source.to_string(),
        description: description.to_string(),
    }
}

#[derive(Debug, Serialize)]
pub struct EvidenceRequirements {
    /// Stable evidence requirement codes derived deterministically from discovery signals.
    pub required: Vec<String>,
    /// Required evidence that is present in the current event bundle.
    pub satisfied: Vec<String>,
    /// Required evidence that is not present in the current event bundle.
    pub missing: Vec<String>,
    /// Additive structured requirements (backward compatible with string arrays).
    pub required_requirements: Vec<Requirement>,
    /// Additive structured satisfied requirements (backward compatible with string arrays).
    pub satisfied_requirements: Vec<Requirement>,
    /// Additive structured missing requirements (backward compatible with string arrays).
    pub missing_requirements: Vec<Requirement>,
}

#[derive(Debug, Serialize)]
pub struct ComplianceCurrentState {
    pub schema_version: String,
    pub run_id: String,
    pub identifiers: CanonicalIdentifiers,
    pub system: SystemIdentityState,
    pub dataset: Option<DatasetGovernanceSummary>,
    pub model: ModelIdentityState,
    pub risks: Option<RiskSummary>,
    pub approval: ApprovalState,
    pub evidence: EvidenceState,
    /// Deterministic AI discovery signals reported into the evidence ledger (event_type `ai_discovery_reported`).
    pub discovery: DiscoverySignals,
    /// Evidence requirements derived from discovery signals.
    pub requirements: EvidenceRequirements,
}

fn payload_get_bool_default(p: &Value, key: &str, default: bool) -> bool {
    payload_get_bool(p, key).unwrap_or(default)
}

fn has_event_type(events: &[EvidenceEvent], event_type: &str) -> bool {
    events.iter().any(|e| e.event_type == event_type)
}

fn has_evidence(events: &[EvidenceEvent], code: &str) -> bool {
    match code {
        // Mandatory: discovery must have been reported for the run.
        "ai_discovery_completed" => has_event_type(events, "ai_discovery_reported"),

        // OpenAI discovery-driven evidence
        "model_registered" => has_event_type(events, "model_registered"),
        "usage_policy_defined" => has_event_type(events, "usage_policy_defined"),

        // Local model / evaluation evidence
        // Deterministic mapping: treat `evaluation_reported` as a completed evaluation signal.
        "evaluation_completed" => {
            has_event_type(events, "evaluation_completed")
                || has_event_type(events, "evaluation_reported")
        }

        // Model artifact documentation evidence
        "model_artifact_documented" => has_event_type(events, "model_artifact_documented"),

        // Unknown codes are treated as missing (defensive, deterministic).
        _ => false,
    }
}

fn derive_discovery_signals(events: &[EvidenceEvent]) -> DiscoverySignals {
    let Some(ev) = find_last_event(events, "ai_discovery_reported") else {
        return DiscoverySignals {
            openai: false,
            transformers: false,
            model_artifacts: false,
        };
    };
    let p = &ev.payload;
    DiscoverySignals {
        openai: payload_get_bool_default(p, "openai", false),
        transformers: payload_get_bool_default(p, "transformers", false),
        model_artifacts: payload_get_bool_default(p, "model_artifacts", false),
    }
}

fn derive_evidence_requirements(
    events: &[EvidenceEvent],
    discovery: &DiscoverySignals,
) -> EvidenceRequirements {
    let mut required: BTreeSet<&'static str> = BTreeSet::new();

    // Mandatory: discovery must be completed for every run (even if it reports no findings).
    required.insert("ai_discovery_completed");

    if discovery.openai {
        required.insert("model_registered");
        required.insert("usage_policy_defined");
    }
    if discovery.transformers {
        required.insert("evaluation_completed");
    }
    if discovery.model_artifacts {
        required.insert("model_artifact_documented");
        required.insert("evaluation_completed");
    }

    let required_vec: Vec<String> = required.iter().copied().map(|s| s.to_string()).collect();
    let satisfied_vec: Vec<String> = required
        .iter()
        .copied()
        .filter(|code| has_evidence(events, code))
        .map(|s| s.to_string())
        .collect();
    let missing_vec: Vec<String> = required
        .iter()
        .copied()
        .filter(|code| !has_evidence(events, code))
        .map(|s| s.to_string())
        .collect();

    EvidenceRequirements {
        required: required_vec,
        satisfied: satisfied_vec,
        missing: missing_vec,
        required_requirements: required
            .iter()
            .copied()
            .map(to_requirement)
            .collect::<Vec<_>>(),
        satisfied_requirements: required
            .iter()
            .copied()
            .filter(|code| has_evidence(events, code))
            .map(to_requirement)
            .collect::<Vec<_>>(),
        missing_requirements: required
            .iter()
            .copied()
            .filter(|code| !has_evidence(events, code))
            .map(to_requirement)
            .collect::<Vec<_>>(),
    }
}

pub fn derive_current_state_from_events_with_context(
    run_id: &str,
    events: &[EvidenceEvent],
    bundle_hash: Option<String>,
    bundle_generated_at: Option<String>,
) -> ComplianceCurrentState {
    let dataset_event = find_last_event(events, "data_registered");
    let ai_system_id = find_last_payload_str_for_event_types(
        events,
        &[
            "data_registered",
            "model_trained",
            "evaluation_reported",
            "risk_recorded",
            "risk_mitigated",
            "risk_reviewed",
            "human_approved",
            "model_promoted",
        ],
        "ai_system_id",
    );
    let dataset_id = find_last_payload_str_for_event_types(
        events,
        &[
            "data_registered",
            "model_trained",
            "evaluation_reported",
            "risk_recorded",
            "risk_mitigated",
            "risk_reviewed",
            "human_approved",
            "model_promoted",
        ],
        "dataset_id",
    );
    let model_version_id = find_last_payload_str_for_event_types(
        events,
        &[
            "model_trained",
            "evaluation_reported",
            "risk_recorded",
            "risk_mitigated",
            "risk_reviewed",
            "human_approved",
            "model_promoted",
        ],
        "model_version_id",
    );

    // Dataset governance is committed in the most recent data_registered payload.
    let dataset = dataset_event.map(|e| DatasetGovernanceSummary {
        dataset_id: payload_get_str(&e.payload, "dataset_id"),
        dataset_governance_id: payload_get_str(&e.payload, "dataset_governance_id"),
        dataset_governance_version: payload_get_str(&e.payload, "dataset_version"),
        dataset_fingerprint: payload_get_str(&e.payload, "dataset_fingerprint"),
        dataset_governance_commitment: payload_get_str(&e.payload, "dataset_governance_commitment"),
        governance_status: payload_get_str(&e.payload, "governance_status"),
    });

    let evaluation_event = find_last_event(events, "evaluation_reported");
    let evaluation_passed = evaluation_event.and_then(|e| payload_get_bool(&e.payload, "passed"));

    // Risk aggregation: for each risk_id, take latest risk_reviewed if present, else latest record/mitigation.
    let mut risk_ids: BTreeMap<String, ()> = BTreeMap::new();
    for e in events.iter() {
        if !matches!(
            e.event_type.as_str(),
            "risk_recorded" | "risk_mitigated" | "risk_reviewed"
        ) {
            continue;
        }
        if let Some(rid) = payload_get_str(&e.payload, "risk_id") {
            risk_ids.insert(rid, ());
        }
    }

    let mut by_risk_class: BTreeMap<String, usize> = BTreeMap::new();
    let mut risks: Vec<RiskRecordSummary> = Vec::new();

    let canonical_risk_ids: Vec<String> = risk_ids.keys().cloned().collect();

    for rid in risk_ids.keys() {
        let recorded = events.iter().rev().find(|e| {
            e.event_type == "risk_recorded"
                && payload_get_str(&e.payload, "risk_id").as_deref() == Some(rid.as_str())
        });
        let mitigated = events.iter().rev().find(|e| {
            e.event_type == "risk_mitigated"
                && payload_get_str(&e.payload, "risk_id").as_deref() == Some(rid.as_str())
        });
        let reviewed = events.iter().rev().find(|e| {
            e.event_type == "risk_reviewed"
                && payload_get_str(&e.payload, "risk_id").as_deref() == Some(rid.as_str())
        });

        // Use recorded payload as the base for classification/severity/likelihood, because mitigations may omit it.
        let base_payload = recorded
            .map(|e| &e.payload)
            .or(mitigated.map(|e| &e.payload));
        let status_event_payload = mitigated.or(recorded).or(reviewed);

        let risk_class = base_payload.and_then(|p| payload_get_str(p, "risk_class"));
        if let Some(rc) = risk_class.clone() {
            *by_risk_class.entry(rc).or_insert(0) += 1;
        }

        let latest_review = reviewed.map(|e| RiskReviewSummary {
            decision: payload_get_str(&e.payload, "decision"),
            reviewer: payload_get_str(&e.payload, "reviewer"),
            justification: payload_get_str(&e.payload, "justification"),
            ts_utc: Some(e.ts_utc.clone()),
            risk_review_event_id: Some(e.event_id.clone()),
        });

        let status_payload = status_event_payload
            .map(|e| &e.payload)
            .unwrap_or(&Value::Null);
        let status = payload_get_str(status_payload, "status");
        let mitigation = payload_get_str(status_payload, "mitigation");
        let owner = payload_get_str(status_payload, "owner");

        let severity = base_payload.and_then(|p| payload_get_num(p, "severity"));
        let likelihood = base_payload.and_then(|p| payload_get_num(p, "likelihood"));
        let ai_system_id_for_risk = base_payload
            .and_then(|p| payload_get_str(p, "ai_system_id"))
            .or_else(|| payload_get_str(status_payload, "ai_system_id"));
        let dataset_id_for_risk = base_payload
            .and_then(|p| payload_get_str(p, "dataset_id"))
            .or_else(|| payload_get_str(status_payload, "dataset_id"));
        let model_version_id_for_risk = base_payload
            .and_then(|p| payload_get_str(p, "model_version_id"))
            .or_else(|| payload_get_str(status_payload, "model_version_id"));

        risks.push(RiskRecordSummary {
            risk_id: rid.clone(),
            ai_system_id: ai_system_id_for_risk,
            dataset_id: dataset_id_for_risk,
            model_version_id: model_version_id_for_risk,
            risk_class,
            severity,
            likelihood,
            status,
            mitigation,
            owner,
            latest_review,
        });
    }

    let risks_summary = if risks.is_empty() {
        None
    } else {
        Some(RiskSummary {
            total_risks: risks.len(),
            by_risk_class,
            risks,
        })
    };

    // Promotion state (derived purely from event existence and payload linkage).
    let human_approval = find_last_event_by_scope(events, "human_approved", "model_promoted");
    let human_approval_decision =
        human_approval.and_then(|e| payload_get_str(&e.payload, "decision"));
    let approved_human_event_id = human_approval.map(|e| e.event_id.clone());
    let approval_scope = human_approval.and_then(|e| payload_get_str(&e.payload, "scope"));
    let approver = human_approval.and_then(|e| payload_get_str(&e.payload, "approver"));
    let approved_at = human_approval.map(|e| e.ts_utc.clone());

    let risk_review_approved = events.iter().rev().find(|e| {
        e.event_type == "risk_reviewed"
            && payload_get_str(&e.payload, "decision").as_deref() == Some("approve")
    });
    let risk_review_decision =
        risk_review_approved.and_then(|e| payload_get_str(&e.payload, "decision"));

    let model_promoted_present = find_last_event(events, "model_promoted").is_some();

    let promotion = if model_promoted_present {
        PromotionState {
            state: "promoted".to_string(),
            reason: None,
            model_promoted_present: true,
        }
    } else if human_approval_decision.as_deref() == Some("approve") {
        PromotionState {
            state: if evaluation_passed == Some(true) {
                "awaiting_promotion_execution".to_string()
            } else {
                "awaiting_evaluation_passed".to_string()
            },
            reason: None,
            model_promoted_present: false,
        }
    } else if risk_review_decision.as_deref() == Some("approve") {
        PromotionState {
            state: "awaiting_human_approval".to_string(),
            reason: None,
            model_promoted_present: false,
        }
    } else {
        PromotionState {
            state: "awaiting_risk_review".to_string(),
            reason: None,
            model_promoted_present: false,
        }
    };

    let primary_risk_id = canonical_risk_ids.first().cloned();
    let latest_event_ts_utc = events.last().map(|e| e.ts_utc.clone());

    let discovery = derive_discovery_signals(events);
    let requirements = derive_evidence_requirements(events, &discovery);

    ComplianceCurrentState {
        run_id: run_id.to_string(),
        schema_version: "aigov.compliance_current_state.v2".to_string(),
        identifiers: CanonicalIdentifiers {
            ai_system_id: ai_system_id.clone(),
            dataset_id: dataset_id.clone(),
            model_version_id: model_version_id.clone(),
            primary_risk_id,
            risk_ids: canonical_risk_ids,
        },
        system: SystemIdentityState { ai_system_id },
        dataset,
        model: ModelIdentityState {
            model_version_id,
            evaluation_passed,
            promotion,
        },
        risks: risks_summary,
        approval: ApprovalState {
            scope: approval_scope,
            approver,
            approved_at,
            risk_review_decision,
            human_approval_decision,
            approved_human_event_id,
        },
        evidence: EvidenceState {
            events_total: events.len(),
            latest_event_ts_utc,
            bundle_hash,
            bundle_generated_at,
        },
        discovery,
        requirements,
    }
}

pub fn derive_current_state_from_events(
    run_id: &str,
    events: &[EvidenceEvent],
) -> ComplianceCurrentState {
    derive_current_state_from_events_with_context(run_id, events, None, None)
}

pub fn derive_current_state_from_bundle_doc(bundle_doc: &Value) -> Option<ComplianceCurrentState> {
    let run_id = bundle_doc.get("run_id")?.as_str()?.to_string();
    let events_val = bundle_doc.get("events")?.clone();
    let events: Vec<EvidenceEvent> = serde_json::from_value(events_val).ok()?;
    Some(derive_current_state_from_events(&run_id, &events))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::compliance_summary::derive_verdict_from_state;
    use crate::policy_config::PolicyConfig;
    use crate::schema::EvidenceEvent;
    use serde_json::json;

    fn ev(id: &str, et: &str, ts: &str, rid: &str, payload: serde_json::Value) -> EvidenceEvent {
        EvidenceEvent {
            event_id: id.to_string(),
            event_type: et.to_string(),
            ts_utc: ts.to_string(),
            actor: "test".to_string(),
            system: "test".to_string(),
            run_id: rid.to_string(),
            environment: None,
            payload,
            parent_run_id: None,
            root_run_id: None,
            delegated_from_event_id: None,
            agent_id: None,
            agent_role: None,
            delegation_reason: None,
        }
    }

    fn discovery(rid: &str, id: &str, openai: bool, transformers: bool, model_artifacts: bool) -> EvidenceEvent {
        ev(
            id,
            "ai_discovery_reported",
            "2026-01-01T00:00:01Z",
            rid,
            json!({
                "openai": openai,
                "transformers": transformers,
                "model_artifacts": model_artifacts
            }),
        )
    }

    fn golden_lifecycle_events(rid: &str) -> Vec<EvidenceEvent> {
        vec![
            discovery(rid, &format!("{rid}-disc"), false, false, false),
            ev(
                &format!("{rid}-data"),
                "data_registered",
                "2026-01-01T00:00:02Z",
                rid,
                json!({
                    "ai_system_id": "as-1",
                    "dataset_id": "ds-1",
                    "dataset_version": "v1",
                    "dataset_fingerprint": "fp",
                    "dataset_governance_id": "dg-1",
                    "governance_status": "registered"
                }),
            ),
            ev(
                &format!("{rid}-train"),
                "model_trained",
                "2026-01-01T00:00:03Z",
                rid,
                json!({
                    "model_version_id": "mv-1",
                    "ai_system_id": "as-1",
                    "dataset_id": "ds-1",
                    "artifact_path": "registry://test/model",
                    "artifact_sha256": "abc1234567890123456789012345678901234567890123456789012345678901234"
                }),
            ),
            ev(
                &format!("{rid}-eval"),
                "evaluation_reported",
                "2026-01-01T00:00:04Z",
                rid,
                json!({
                    "ai_system_id": "as-1",
                    "dataset_id": "ds-1",
                    "model_version_id": "mv-1",
                    "passed": true
                }),
            ),
            ev(
                &format!("{rid}-risk"),
                "risk_recorded",
                "2026-01-01T00:00:05Z",
                rid,
                json!({
                    "risk_id": "risk-1",
                    "risk_class": "high",
                    "severity": 4.0,
                    "likelihood": 0.3,
                    "status": "submitted",
                    "ai_system_id": "as-1",
                    "dataset_id": "ds-1",
                    "model_version_id": "mv-1"
                }),
            ),
            ev(
                &format!("{rid}-review"),
                "risk_reviewed",
                "2026-01-01T00:00:06Z",
                rid,
                json!({
                    "risk_id": "risk-1",
                    "decision": "approve",
                    "reviewer": "risk_officer",
                    "justification": "acceptable",
                    "ai_system_id": "as-1",
                    "dataset_id": "ds-1",
                    "model_version_id": "mv-1"
                }),
            ),
            ev(
                &format!("{rid}-human"),
                "human_approved",
                "2026-01-01T00:00:07Z",
                rid,
                json!({
                    "scope": "model_promoted",
                    "decision": "approve",
                    "approver": "compliance_officer",
                    "risk_id": "risk-1",
                    "ai_system_id": "as-1",
                    "dataset_id": "ds-1",
                    "model_version_id": "mv-1"
                }),
            ),
            ev(
                &format!("{rid}-promote"),
                "model_promoted",
                "2026-01-01T00:00:08Z",
                rid,
                json!({
                    "ai_system_id": "as-1",
                    "dataset_id": "ds-1",
                    "model_version_id": "mv-1",
                    "artifact_path": "registry://test/model",
                    "approved_human_event_id": format!("{rid}-human")
                }),
            ),
        ]
    }

    #[test]
    fn valid_lifecycle_projection() {
        let rid = "proj-valid";
        let events = golden_lifecycle_events(rid);
        let state = derive_current_state_from_events(rid, &events);
        assert_eq!(state.schema_version, "aigov.compliance_current_state.v2");
        assert_eq!(state.identifiers.ai_system_id.as_deref(), Some("as-1"));
        assert_eq!(state.model.evaluation_passed, Some(true));
        assert_eq!(state.model.promotion.state, "promoted");
        assert!(state.model.promotion.model_promoted_present);
        assert!(state.requirements.missing.is_empty());
        assert_eq!(state.evidence.events_total, events.len());

        let outcome = derive_verdict_from_state(&state, &PolicyConfig::default());
        assert_eq!(outcome.verdict, "VALID");
    }

    #[test]
    fn blocked_missing_evidence_projection() {
        let rid = "proj-blocked";
        let events = vec![
            discovery(rid, "d1", true, false, false),
            // openai discovery requires model_registered + usage_policy_defined
        ];
        let state = derive_current_state_from_events(rid, &events);
        assert!(state
            .requirements
            .missing
            .contains(&"model_registered".to_string()));
        assert!(state
            .requirements
            .missing
            .contains(&"usage_policy_defined".to_string()));
        assert_eq!(state.model.promotion.state, "awaiting_risk_review");

        let outcome = derive_verdict_from_state(&state, &PolicyConfig::default());
        assert_eq!(outcome.verdict, "BLOCKED");
    }

    #[test]
    fn invalid_evaluation_projection() {
        let rid = "proj-invalid";
        let events = vec![
            discovery(rid, "d1", false, false, false),
            ev(
                "e1",
                "evaluation_reported",
                "2026-01-01T00:00:02Z",
                rid,
                json!({
                    "ai_system_id": "as-1",
                    "dataset_id": "ds-1",
                    "model_version_id": "mv-1",
                    "passed": false
                }),
            ),
        ];
        let state = derive_current_state_from_events(rid, &events);
        assert_eq!(state.model.evaluation_passed, Some(false));

        let outcome = derive_verdict_from_state(&state, &PolicyConfig::default());
        assert_eq!(outcome.verdict, "INVALID");
    }

    #[test]
    fn promotion_edge_cases() {
        let rid = "proj-promo";
        let base = || {
            vec![
                discovery(rid, "d1", false, false, false),
                ev(
                    "risk",
                    "risk_recorded",
                    "2026-01-01T00:00:02Z",
                    rid,
                    json!({"risk_id": "r1", "risk_class": "low"}),
                ),
            ]
        };

        let awaiting_risk = derive_current_state_from_events(rid, &base());
        assert_eq!(awaiting_risk.model.promotion.state, "awaiting_risk_review");

        let mut after_review = base();
        after_review.push(ev(
            "review",
            "risk_reviewed",
            "2026-01-01T00:00:03Z",
            rid,
            json!({"risk_id": "r1", "decision": "approve"}),
        ));
        let awaiting_human = derive_current_state_from_events(rid, &after_review);
        assert_eq!(awaiting_human.model.promotion.state, "awaiting_human_approval");

        let mut after_human = after_review.clone();
        after_human.push(ev(
            "human",
            "human_approved",
            "2026-01-01T00:00:04Z",
            rid,
            json!({"scope": "model_promoted", "decision": "approve"}),
        ));
        let awaiting_eval = derive_current_state_from_events(rid, &after_human);
        assert_eq!(
            awaiting_eval.model.promotion.state,
            "awaiting_evaluation_passed"
        );

        after_human.push(ev(
            "eval",
            "evaluation_reported",
            "2026-01-01T00:00:05Z",
            rid,
            json!({"passed": true, "model_version_id": "mv-1"}),
        ));
        let awaiting_exec = derive_current_state_from_events(rid, &after_human);
        assert_eq!(
            awaiting_exec.model.promotion.state,
            "awaiting_promotion_execution"
        );

        after_human.push(ev(
            "promote",
            "model_promoted",
            "2026-01-01T00:00:06Z",
            rid,
            json!({"model_version_id": "mv-1"}),
        ));
        let promoted = derive_current_state_from_events(rid, &after_human);
        assert_eq!(promoted.model.promotion.state, "promoted");
    }

    #[test]
    fn risk_review_decision_propagation() {
        let rid = "proj-risk";
        let events = vec![
            discovery(rid, "d1", false, false, false),
            ev(
                "rec",
                "risk_recorded",
                "2026-01-01T00:00:02Z",
                rid,
                json!({
                    "risk_id": "risk-9",
                    "risk_class": "medium",
                    "severity": 2.0,
                    "likelihood": 0.5,
                    "status": "open"
                }),
            ),
            ev(
                "rev",
                "risk_reviewed",
                "2026-01-01T00:00:03Z",
                rid,
                json!({
                    "risk_id": "risk-9",
                    "decision": "approve",
                    "reviewer": "alice",
                    "justification": "mitigated"
                }),
            ),
        ];
        let state = derive_current_state_from_events(rid, &events);
        assert_eq!(state.approval.risk_review_decision.as_deref(), Some("approve"));

        let risks = state.risks.expect("risk summary");
        assert_eq!(risks.total_risks, 1);
        let review = risks.risks[0]
            .latest_review
            .as_ref()
            .expect("latest review");
        assert_eq!(review.decision.as_deref(), Some("approve"));
        assert_eq!(review.reviewer.as_deref(), Some("alice"));
        assert_eq!(review.risk_review_event_id.as_deref(), Some("rev"));
    }
}
