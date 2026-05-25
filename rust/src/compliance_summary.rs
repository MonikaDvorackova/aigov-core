//! Ledger-authoritative compliance verdict (`VALID` / `INVALID` / `BLOCKED`).

use crate::policy_config::PolicyConfig;
use crate::projection::ComplianceCurrentState;
use serde::Serialize;
use serde_json::{json, Value};

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct BlockedReason {
    pub code: String,
    pub message: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VerdictOutcome {
    pub verdict: String,
    pub reason_codes: Vec<String>,
    pub blocked_reasons: Vec<BlockedReason>,
    pub missing_evidence: Vec<String>,
}

pub fn derive_verdict_from_state(
    state: &ComplianceCurrentState,
    _policy_cfg: &PolicyConfig,
) -> VerdictOutcome {
    let mut reason_codes: Vec<String> = Vec::new();
    let mut blocked_reasons: Vec<BlockedReason> = Vec::new();
    let missing_evidence = state.requirements.missing.clone();

    if state.model.evaluation_passed == Some(false) {
        reason_codes.push("evaluation_failed".to_string());
        return VerdictOutcome {
            verdict: "INVALID".to_string(),
            reason_codes,
            blocked_reasons,
            missing_evidence,
        };
    }

    if state.approval.risk_review_decision.as_deref() == Some("reject") {
        reason_codes.push("risk_review_rejected".to_string());
        blocked_reasons.push(BlockedReason {
            code: "risk_review_rejected".to_string(),
            message: "Risk review recorded a reject decision for this run.".to_string(),
        });
        return VerdictOutcome {
            verdict: "BLOCKED".to_string(),
            reason_codes,
            blocked_reasons,
            missing_evidence,
        };
    }

    if state.approval.human_approval_decision.as_deref() == Some("reject") {
        reason_codes.push("human_approval_rejected".to_string());
        blocked_reasons.push(BlockedReason {
            code: "human_approval_rejected".to_string(),
            message: "Human approval recorded a reject decision for this run.".to_string(),
        });
        return VerdictOutcome {
            verdict: "BLOCKED".to_string(),
            reason_codes,
            blocked_reasons,
            missing_evidence,
        };
    }

    if !missing_evidence.is_empty() {
        for code in &missing_evidence {
            reason_codes.push(format!("missing_{code}"));
        }
        blocked_reasons.push(BlockedReason {
            code: "missing_required_evidence".to_string(),
            message: format!(
                "Required evidence not satisfied: {}",
                missing_evidence.join(", ")
            ),
        });
        return VerdictOutcome {
            verdict: "BLOCKED".to_string(),
            reason_codes,
            blocked_reasons,
            missing_evidence,
        };
    }

    if state.model.promotion.state != "promoted" {
        let (code, message) = promotion_blocked_reason(&state.model.promotion.state);
        reason_codes.push(code.clone());
        blocked_reasons.push(BlockedReason { code, message });
        return VerdictOutcome {
            verdict: "BLOCKED".to_string(),
            reason_codes,
            blocked_reasons,
            missing_evidence,
        };
    }

    VerdictOutcome {
        verdict: "VALID".to_string(),
        reason_codes,
        blocked_reasons,
        missing_evidence,
    }
}

fn promotion_blocked_reason(promotion_state: &str) -> (String, String) {
    match promotion_state {
        "awaiting_risk_review" => (
            "awaiting_risk_review".to_string(),
            "Run is blocked until risk review approves the assessment.".to_string(),
        ),
        "awaiting_human_approval" => (
            "awaiting_human_approval".to_string(),
            "Run is blocked until human approval for promotion is recorded.".to_string(),
        ),
        "awaiting_evaluation_passed" => (
            "awaiting_evaluation_passed".to_string(),
            "Run is blocked until a passing evaluation is recorded.".to_string(),
        ),
        "awaiting_promotion_execution" => (
            "awaiting_promotion_execution".to_string(),
            "Approval prerequisites are satisfied; model promotion has not been executed.".to_string(),
        ),
        _ => (
            "awaiting_approval_or_promotion".to_string(),
            "Run is not yet promotable: approval/promotion prerequisites are not satisfied.".to_string(),
        ),
    }
}

pub fn compliance_summary_success_json(
    run_id: &str,
    policy_version: &str,
    current_state: &ComplianceCurrentState,
    outcome: &VerdictOutcome,
) -> Value {
    let current_state_json =
        serde_json::to_value(current_state).expect("ComplianceCurrentState serializes");
    json!({
        "ok": true,
        "schema_version": "aigov.compliance_summary.v2",
        "policy_version": policy_version,
        "run_id": run_id,
        "verdict": outcome.verdict,
        "reason_codes": outcome.reason_codes,
        "missing_evidence": outcome.missing_evidence,
        "blocked_reasons": outcome.blocked_reasons,
        "current_state": current_state_json,
    })
}

pub fn compliance_summary_error_json(
    run_id: &str,
    policy_version: &str,
    error: &str,
    message: &str,
    details: Option<&str>,
) -> Value {
    let mut body = json!({
        "ok": false,
        "schema_version": "aigov.compliance_summary.v2",
        "error": error,
        "code": error,
        "message": message,
        "policy_version": policy_version,
        "run_id": run_id,
    });
    if let Some(d) = details {
        body["details"] = json!(d);
    }
    body
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::projection::derive_current_state_from_events;
    use crate::schema::EvidenceEvent;

    fn ev(id: &str, et: &str, ts: &str, rid: &str, payload: serde_json::Value) -> EvidenceEvent {
        EvidenceEvent {
            event_id: id.to_string(),
            event_type: et.to_string(),
            ts_utc: ts.to_string(),
            actor: "a".to_string(),
            system: "s".to_string(),
            run_id: rid.to_string(),
            environment: None,
            payload,
        }
    }

    #[test]
    fn blocked_when_discovery_missing() {
        let rid = "run-blocked";
        let events = vec![];
        let state = derive_current_state_from_events(rid, &events);
        let outcome = derive_verdict_from_state(&state, &PolicyConfig::default());
        assert_eq!(outcome.verdict, "BLOCKED");
        assert!(outcome
            .missing_evidence
            .contains(&"ai_discovery_completed".to_string()));
    }

    #[test]
    fn invalid_when_evaluation_failed() {
        let rid = "run-invalid";
        let events = vec![
            ev(
                "d1",
                "ai_discovery_reported",
                "2026-01-01T00:00:01Z",
                rid,
                json!({"openai": false, "transformers": false, "model_artifacts": false}),
            ),
            ev(
                "e1",
                "evaluation_reported",
                "2026-01-01T00:00:02Z",
                rid,
                json!({
                    "ai_system_id": "as1",
                    "dataset_id": "ds1",
                    "model_version_id": "mv1",
                    "metric": "accuracy",
                    "value": 0.1,
                    "threshold": 0.8,
                    "passed": false
                }),
            ),
        ];
        let state = derive_current_state_from_events(rid, &events);
        let outcome = derive_verdict_from_state(&state, &PolicyConfig::default());
        assert_eq!(outcome.verdict, "INVALID");
        assert!(outcome.reason_codes.contains(&"evaluation_failed".to_string()));
    }
}
