//! Governance projection and human-readable replay explanations.

use crate::compliance_summary::{derive_verdict_from_state, VerdictOutcome};
use crate::policy_config::PolicyConfig;
use crate::projection::{derive_current_state_from_events_with_context, ComplianceCurrentState};
use crate::schema::EvidenceEvent;
use serde::Serialize;
use std::collections::BTreeSet;

#[derive(Debug, Clone, Serialize)]
pub struct LifecycleTransition {
    pub event_id: String,
    pub event_type: String,
    pub ts_utc: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct GateContribution {
    pub gate: String,
    pub status: String,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ReplayExplanation {
    pub verdict_summary: String,
    pub why_blocked: Vec<String>,
    pub what_unlocked_valid: Vec<String>,
    pub gate_contributions: Vec<GateContribution>,
    pub lifecycle_transitions: Vec<LifecycleTransition>,
}

#[derive(Debug, Serialize)]
pub struct ReplayProjection {
    pub current_state: ComplianceCurrentState,
    pub outcome: VerdictOutcome,
    pub explanation: ReplayExplanation,
}

pub fn build_lifecycle_transitions(events: &[EvidenceEvent]) -> Vec<LifecycleTransition> {
    let governance_types = BTreeSet::from([
        "ai_discovery_reported",
        "data_registered",
        "model_trained",
        "evaluation_reported",
        "risk_recorded",
        "risk_reviewed",
        "human_approved",
        "model_promoted",
        "policy_evaluation",
        "tool_call",
        "tool_output",
        "ai_decision_completed",
    ]);
    let mut ordered = events.to_vec();
    ordered.sort_by(|a, b| {
        a.ts_utc
            .cmp(&b.ts_utc)
            .then_with(|| a.event_type.cmp(&b.event_type))
            .then_with(|| a.event_id.cmp(&b.event_id))
    });
    ordered
        .into_iter()
        .filter(|e| governance_types.contains(e.event_type.as_str()))
        .map(|e| LifecycleTransition {
            event_id: e.event_id,
            event_type: e.event_type,
            ts_utc: e.ts_utc,
        })
        .collect()
}

pub fn project_governance_state(
    run_id: &str,
    events: &[EvidenceEvent],
    bundle_sha256: Option<String>,
    exported_at: Option<String>,
    policy_cfg: &PolicyConfig,
) -> ReplayProjection {
    let state = derive_current_state_from_events_with_context(
        run_id,
        events,
        bundle_sha256,
        exported_at,
    );
    let outcome = derive_verdict_from_state(&state, policy_cfg);
    let lifecycle_transitions = build_lifecycle_transitions(events);
    let explanation = explain_verdict(&state, &outcome, &lifecycle_transitions);
    ReplayProjection {
        current_state: state,
        outcome,
        explanation,
    }
}

fn explain_verdict(
    state: &ComplianceCurrentState,
    outcome: &VerdictOutcome,
    transitions: &[LifecycleTransition],
) -> ReplayExplanation {
    let mut gates = Vec::new();

    gates.push(GateContribution {
        gate: "evaluation".to_string(),
        status: match state.model.evaluation_passed {
            Some(true) => "passed",
            Some(false) => "failed",
            None => "missing",
        }
        .to_string(),
        detail: match state.model.evaluation_passed {
            Some(true) => "evaluation_reported with passed=true".to_string(),
            Some(false) => "evaluation_reported with passed=false (INVALID)".to_string(),
            None => "no passing evaluation evidence in replay".to_string(),
        },
    });

    gates.push(GateContribution {
        gate: "human_approval".to_string(),
        status: state
            .approval
            .human_approval_decision
            .as_deref()
            .unwrap_or("missing")
            .to_string(),
        detail: format!(
            "promotion state={:?}, approver={:?}",
            state.model.promotion.state, state.approval.approver
        ),
    });

    gates.push(GateContribution {
        gate: "evidence_requirements".to_string(),
        status: if state.requirements.missing.is_empty() {
            "satisfied".to_string()
        } else {
            "missing".to_string()
        },
        detail: if state.requirements.missing.is_empty() {
            "all discovery-derived requirements present".to_string()
        } else {
            format!("missing: {}", state.requirements.missing.join(", "))
        },
    });

    let mut why_blocked = Vec::new();
    let mut what_unlocked = Vec::new();

    for reason in &outcome.blocked_reasons {
        why_blocked.push(format!("{}: {}", reason.code, reason.message));
    }
    for code in &outcome.reason_codes {
        if code.starts_with("missing_") {
            why_blocked.push(format!("Missing required evidence ({code})"));
        }
    }

    if outcome.verdict == "VALID" {
        what_unlocked.push("All governance gates satisfied; model promotion state is promoted.".to_string());
        if transitions.iter().any(|t| t.event_type == "human_approved") {
            what_unlocked.push("human_approved evidence recorded.".to_string());
        }
        if transitions.iter().any(|t| t.event_type == "evaluation_reported") {
            what_unlocked.push("evaluation_reported with passed=true.".to_string());
        }
    } else if outcome.verdict == "BLOCKED" {
        if state.model.promotion.state != "promoted" {
            why_blocked.push(format!(
                "Promotion gate: state is {:?}",
                state.model.promotion.state
            ));
        }
        if state.approval.human_approval_decision.is_none() {
            why_blocked.push("Human approval not yet recorded in evidence.".to_string());
        }
    } else if outcome.verdict == "INVALID" {
        why_blocked.push("Evaluation gate failed (evaluation_passed=false).".to_string());
    }

    let verdict_summary = format!(
        "Replayed verdict {} from {} lifecycle evidence events (promotion={:?}).",
        outcome.verdict,
        transitions.len(),
        state.model.promotion.state
    );

    ReplayExplanation {
        verdict_summary,
        why_blocked,
        what_unlocked_valid: what_unlocked,
        gate_contributions: gates,
        lifecycle_transitions: transitions.to_vec(),
    }
}
