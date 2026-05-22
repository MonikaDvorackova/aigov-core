use crate::audit_store::StoredRecord;
use crate::policy_config::{effective_approver_allowlist, PolicyConfig};
use crate::schema::EvidenceEvent;
use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::{BufRead, BufReader};

/// Structured policy enforcement failure (stable code + human message).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PolicyViolation {
    pub code: String,
    pub message: String,
}

impl PolicyViolation {
    fn new(code: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            code: code.into(),
            message: message.into(),
        }
    }
}

impl std::fmt::Display for PolicyViolation {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        // Back-compat: most callers historically treated policy errors as strings.
        f.write_str(&self.message)
    }
}

impl std::error::Error for PolicyViolation {}

// Stable codes for major enforcement gates.
const CODE_MISSING_DATA_REGISTERED: &str = "missing_data_registered";
const CODE_MISSING_RISK_REVIEW_FOR_APPROVAL: &str = "missing_risk_review_for_approval";
const CODE_MISSING_PASSED_EVALUATION_FOR_PROMOTION: &str =
    "missing_passed_evaluation_for_promotion";
const CODE_MISSING_RISK_REVIEW_FOR_PROMOTION: &str = "missing_risk_review_for_promotion";
const CODE_MISSING_HUMAN_APPROVAL_FOR_PROMOTION: &str = "missing_human_approval_for_promotion";
const CODE_APPROVER_NOT_ALLOWLISTED: &str = "approver_not_allowlisted";
const CODE_SCHEMA_INVALID: &str = "schema_invalid";

pub fn enforce(
    event: &EvidenceEvent,
    log_path: &str,
    cfg: &PolicyConfig,
) -> Result<(), PolicyViolation> {
    match event.event_type.as_str() {
        "data_registered" => enforce_data_registered(event),
        "model_trained" => enforce_model_trained(event, log_path, cfg),
        "evaluation_reported" => enforce_evaluation_reported(event),
        "risk_recorded" => enforce_risk_recorded(event),
        "risk_mitigated" => enforce_risk_mitigated(event),
        "risk_reviewed" => enforce_risk_reviewed(event),
        "human_approved" => enforce_human_approved(event, log_path, cfg),
        "model_promoted" => enforce_model_promoted(event, log_path, cfg),
        _ => Ok(()),
    }
}

/* ------------------------- schema checks ------------------------- */

fn enforce_data_registered(event: &EvidenceEvent) -> Result<(), PolicyViolation> {
    let p = &event.payload;

    let ai_system_id_ok = p
        .get("ai_system_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let dataset_id_ok = p
        .get("dataset_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    let dataset_ok = p
        .get("dataset")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let fp_ok = p
        .get("dataset_fingerprint")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    // Dataset governance commitment and minimum governance metadata.
    let governance_id_ok = p
        .get("dataset_governance_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let governance_commitment_ok = p
        .get("dataset_governance_commitment")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    let dataset_version_ok = p
        .get("dataset_version")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let source_ok = p
        .get("source")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let intended_use_ok = p
        .get("intended_use")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let limitations_ok = p
        .get("limitations")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let quality_summary_ok = p
        .get("quality_summary")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let governance_status_ok = p
        .get("governance_status")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    if dataset_ok
        && fp_ok
        && ai_system_id_ok
        && dataset_id_ok
        && governance_id_ok
        && governance_commitment_ok
        && dataset_version_ok
        && source_ok
        && intended_use_ok
        && limitations_ok
        && quality_summary_ok
        && governance_status_ok
    {
        Ok(())
    } else {
        Err(PolicyViolation::new(
            CODE_SCHEMA_INVALID,
            "policy_violation: data_registered payload must include ai_system_id + dataset_id + dataset + dataset_fingerprint + dataset governance fields (id, version, commitment, source, intended_use, limitations, quality_summary, governance_status)",
        ))
    }
}

fn enforce_evaluation_reported(event: &EvidenceEvent) -> Result<(), PolicyViolation> {
    let p = &event.payload;

    let metric_ok = p.get("metric").and_then(|v| v.as_str()).is_some();
    let value_ok = p.get("value").and_then(|v| v.as_f64()).is_some();
    let threshold_ok = p.get("threshold").and_then(|v| v.as_f64()).is_some();
    let passed_ok = p.get("passed").and_then(|v| v.as_bool()).is_some();

    let ai_system_id_ok = p
        .get("ai_system_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let dataset_id_ok = p
        .get("dataset_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let model_version_id_ok = p
        .get("model_version_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    if metric_ok
        && value_ok
        && threshold_ok
        && passed_ok
        && ai_system_id_ok
        && dataset_id_ok
        && model_version_id_ok
    {
        Ok(())
    } else {
        Err(PolicyViolation::new(
            CODE_SCHEMA_INVALID,
            "policy_violation: evaluation_reported payload must include ai_system_id + dataset_id + model_version_id + metric(str), value(number), threshold(number), passed(bool)",
        ))
    }
}

fn enforce_risk_recorded(event: &EvidenceEvent) -> Result<(), PolicyViolation> {
    let p = &event.payload;

    let ai_system_id_ok = p
        .get("ai_system_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let dataset_id_ok = p
        .get("dataset_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let model_version_id_ok = p
        .get("model_version_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    let risk_id_ok = p
        .get("risk_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let assessment_id_ok = p
        .get("assessment_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let dataset_commitment_ok = p
        .get("dataset_governance_commitment")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    let risk_class_ok = p
        .get("risk_class")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    let severity_ok = p.get("severity").and_then(|v| v.as_f64()).is_some();
    let likelihood_ok = p.get("likelihood").and_then(|v| v.as_f64()).is_some();
    let status_ok = p
        .get("status")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let mitigation_ok = p
        .get("mitigation")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let owner_ok = p
        .get("owner")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    if risk_id_ok
        && assessment_id_ok
        && dataset_commitment_ok
        && ai_system_id_ok
        && dataset_id_ok
        && model_version_id_ok
        && risk_class_ok
        && severity_ok
        && likelihood_ok
        && status_ok
        && mitigation_ok
        && owner_ok
    {
        Ok(())
    } else {
        Err(PolicyViolation::new(
            CODE_SCHEMA_INVALID,
            "policy_violation: risk_recorded payload must include risk_id, assessment_id, dataset_governance_commitment, risk_class, severity(number), likelihood(number), status(str), mitigation(str), owner(str)",
        ))
    }
}

fn enforce_risk_mitigated(event: &EvidenceEvent) -> Result<(), PolicyViolation> {
    let p = &event.payload;

    let ai_system_id_ok = p
        .get("ai_system_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let dataset_id_ok = p
        .get("dataset_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let model_version_id_ok = p
        .get("model_version_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    let risk_id_ok = p
        .get("risk_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let assessment_id_ok = p
        .get("assessment_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let dataset_commitment_ok = p
        .get("dataset_governance_commitment")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    let status_ok = p
        .get("status")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let mitigation_ok = p
        .get("mitigation")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    if risk_id_ok
        && assessment_id_ok
        && dataset_commitment_ok
        && ai_system_id_ok
        && dataset_id_ok
        && model_version_id_ok
        && status_ok
        && mitigation_ok
    {
        Ok(())
    } else {
        Err(PolicyViolation::new(
            CODE_SCHEMA_INVALID,
            "policy_violation: risk_mitigated payload must include ai_system_id + dataset_id + model_version_id + risk_id, assessment_id, dataset_governance_commitment, status(str), mitigation(str)",
        ))
    }
}

fn enforce_risk_reviewed(event: &EvidenceEvent) -> Result<(), PolicyViolation> {
    let p = &event.payload;

    let ai_system_id_ok = p
        .get("ai_system_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let dataset_id_ok = p
        .get("dataset_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let model_version_id_ok = p
        .get("model_version_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    let risk_id_ok = p
        .get("risk_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let assessment_id_ok = p
        .get("assessment_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let dataset_commitment_ok = p
        .get("dataset_governance_commitment")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    let decision = p.get("decision").and_then(|v| v.as_str());
    let decision_ok = matches!(decision, Some("approve") | Some("reject"));

    let reviewer_ok = p
        .get("reviewer")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let justification_ok = p
        .get("justification")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    if risk_id_ok
        && assessment_id_ok
        && dataset_commitment_ok
        && ai_system_id_ok
        && dataset_id_ok
        && model_version_id_ok
        && decision_ok
        && reviewer_ok
        && justification_ok
    {
        Ok(())
    } else {
        Err(PolicyViolation::new(
            CODE_SCHEMA_INVALID,
            "policy_violation: risk_reviewed payload must include ai_system_id + dataset_id + model_version_id + risk_id, assessment_id, dataset_governance_commitment, decision(approve|reject), reviewer(str), justification(str)",
        ))
    }
}

// Required payload:
// - scope: "model_promoted"
// - decision: "approve" | "reject"
// - approver: string (person or role)
// - justification: string
// - assessment_id, risk_id, dataset_governance_commitment (linkage)
fn enforce_human_approved(
    event: &EvidenceEvent,
    log_path: &str,
    cfg: &PolicyConfig,
) -> Result<(), PolicyViolation> {
    let p = &event.payload;

    let scope_ok = matches!(
        p.get("scope").and_then(|v| v.as_str()),
        Some("model_promoted")
    );

    let decision = p.get("decision").and_then(|v| v.as_str());
    let decision_ok = matches!(decision, Some("approve") | Some("reject"));

    let approver = p
        .get("approver")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string());
    let approver_ok = approver.as_ref().map(|s| !s.is_empty()).unwrap_or(false);
    let just_ok = p
        .get("justification")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    let assessment_id = p
        .get("assessment_id")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string());
    let risk_id = p
        .get("risk_id")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string());
    let dataset_commitment = p
        .get("dataset_governance_commitment")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string());

    let ai_system_id = p
        .get("ai_system_id")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string());
    let dataset_id = p
        .get("dataset_id")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string());
    let model_version_id = p
        .get("model_version_id")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string());

    if !(scope_ok && decision_ok && approver_ok && just_ok) {
        return Err(PolicyViolation::new(
            CODE_SCHEMA_INVALID,
            "policy_violation: human_approved payload must include scope=model_promoted, decision(approve|reject), approver(str), justification(str), assessment_id(str), risk_id(str), dataset_governance_commitment(str), ai_system_id(str), dataset_id(str), model_version_id(str)",
        ));
    }

    let (assessment_id, risk_id, dataset_commitment, approver, ai_system_id, dataset_id, model_version_id) = match (
        assessment_id,
        risk_id,
        dataset_commitment,
        approver,
        ai_system_id,
        dataset_id,
        model_version_id,
    ) {
        (Some(a), Some(r), Some(d), Some(ap), Some(ai), Some(di), Some(mvi)) => (a, r, d, ap, ai, di, mvi),
        _ => {
            return Err(PolicyViolation::new(
                CODE_SCHEMA_INVALID,
                "policy_violation: human_approved payload missing linkage fields assessment_id/risk_id/dataset_governance_commitment/ai_system_id/dataset_id/model_version_id",
            ))
        }
    };

    if cfg.enforce_approver_allowlist {
        let allowlist = effective_approver_allowlist(cfg);
        if !allowlist.iter().any(|a| a == &approver.to_lowercase()) {
            return Err(PolicyViolation::new(
                CODE_APPROVER_NOT_ALLOWLISTED,
                format!(
                    "policy_violation: human_approved approver '{}' not in allowlist",
                    approver
                ),
            ));
        }
    }

    // Risk review must happen before human approval for promotion when required by policy.
    if cfg.require_risk_review_for_approval
        && !has_risk_reviewed_approved(
            &event.run_id,
            &assessment_id,
            &risk_id,
            &dataset_commitment,
            &ai_system_id,
            &dataset_id,
            &model_version_id,
            log_path,
        )?
    {
        return Err(PolicyViolation::new(
            CODE_MISSING_RISK_REVIEW_FOR_APPROVAL,
            "policy_violation: human_approved requires prior risk_reviewed decision=approve with matching assessment_id/risk_id/dataset_governance_commitment",
        ));
    }

    Ok(())
}

/* ------------------------- ordering / gating ------------------------- */

fn enforce_model_trained(
    event: &EvidenceEvent,
    log_path: &str,
    cfg: &PolicyConfig,
) -> Result<(), PolicyViolation> {
    let p = &event.payload;
    let ai_system_id_ok = p
        .get("ai_system_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let dataset_id_ok = p
        .get("dataset_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let model_version_id_ok = p
        .get("model_version_id")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    if !(ai_system_id_ok && dataset_id_ok && model_version_id_ok) {
        return Err(PolicyViolation::new(
            CODE_SCHEMA_INVALID,
            "policy_violation: model_trained payload must include ai_system_id + dataset_id + model_version_id",
        ));
    }

    if cfg.block_if_missing_evidence
        && !has_event_for_run("data_registered", &event.run_id, log_path)?
    {
        return Err(PolicyViolation::new(
            CODE_MISSING_DATA_REGISTERED,
            "policy_violation: model_trained requires prior data_registered for the same run_id",
        ));
    }

    Ok(())
}

fn enforce_model_promoted(
    event: &EvidenceEvent,
    log_path: &str,
    cfg: &PolicyConfig,
) -> Result<(), PolicyViolation> {
    let p = &event.payload;

    // Schema + linkage validation first; then cross-event gating checks.
    let artifact_path_ok = p
        .get("artifact_path")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    let artifact_digest_ok = p
        .get("artifact_sha256")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().len() == 64)
        .unwrap_or(false)
        || p.get("artifact_digest_sha256")
            .and_then(|v| v.as_str())
            .map(|s| s.trim().len() == 64)
            .unwrap_or(false);
    let promotion_reason_ok = p
        .get("promotion_reason")
        .and_then(|v| v.as_str())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);

    let assessment_id = p
        .get("assessment_id")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string());
    let risk_id = p
        .get("risk_id")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string());
    let dataset_commitment = p
        .get("dataset_governance_commitment")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string());
    let approved_human_event_id = p
        .get("approved_human_event_id")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string());

    let ai_system_id = p
        .get("ai_system_id")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string());
    let dataset_id = p
        .get("dataset_id")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string());
    let model_version_id = p
        .get("model_version_id")
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string());

    if !(artifact_path_ok && promotion_reason_ok && artifact_digest_ok) {
        return Err(PolicyViolation::new(
            CODE_SCHEMA_INVALID,
            "policy_violation: model_promoted payload must include artifact_path(str), promotion_reason(str), and artifact digest (artifact_sha256 or artifact_digest_sha256, 64-char hex)",
        ));
    }

    let (assessment_id, risk_id, dataset_commitment) = match (assessment_id, risk_id, dataset_commitment) {
        (Some(a), Some(r), Some(d)) => (a, r, d),
        _ => {
            return Err(PolicyViolation::new(
                CODE_SCHEMA_INVALID,
                "policy_violation: model_promoted payload missing linkage fields assessment_id/risk_id/dataset_governance_commitment",
            ))
        }
    };

    if cfg.require_approval {
        match approved_human_event_id.as_ref().map(|s| s.trim()) {
            Some(s) if !s.is_empty() => {}
            _ => {
                return Err(PolicyViolation::new(
                    CODE_MISSING_HUMAN_APPROVAL_FOR_PROMOTION,
                    "policy_violation: model_promoted payload missing linkage field approved_human_event_id",
                ));
            }
        }
    }

    let approved_human_event_id = approved_human_event_id.unwrap_or_default();

    let (assessment_id, risk_id, dataset_commitment, ai_system_id, dataset_id, model_version_id) =
        match (
            Some(assessment_id),
            Some(risk_id),
            Some(dataset_commitment),
            ai_system_id,
            dataset_id,
            model_version_id,
        ) {
            (Some(a), Some(r), Some(d), Some(ai), Some(di), Some(mvi)) => (a, r, d, ai, di, mvi),
            _ => {
                return Err(PolicyViolation::new(
                    CODE_SCHEMA_INVALID,
                    "policy_violation: model_promoted payload missing ai_system_id/dataset_id/model_version_id linkage",
                ))
            }
        };

    // Gate 1: requires passed evaluation
    if cfg.require_passed_evaluation_for_promotion
        && !has_passed_evaluation(&event.run_id, log_path)?
    {
        return Err(PolicyViolation::new(
            CODE_MISSING_PASSED_EVALUATION_FOR_PROMOTION,
            "policy_violation: model_promoted requires prior evaluation_reported with passed=true",
        ));
    }

    // Gate 2: requires explicit risk approval for promotion
    if cfg.require_risk_review_for_promotion
        && !has_risk_reviewed_approved(
            &event.run_id,
            &assessment_id,
            &risk_id,
            &dataset_commitment,
            &ai_system_id,
            &dataset_id,
            &model_version_id,
            log_path,
        )?
    {
        return Err(PolicyViolation::new(
            CODE_MISSING_RISK_REVIEW_FOR_PROMOTION,
            "policy_violation: model_promoted blocked by missing or rejected risk_reviewed (requires decision=approve with matching assessment_id/risk_id/dataset_governance_commitment/ai_system_id/dataset_id/model_version_id)",
        ));
    }

    // Gate 3: requires explicit human approval for promotion; must reference the specific approval event.
    if cfg.require_approval
        && !human_approved_event_ok(
            &event.run_id,
            &approved_human_event_id,
            &assessment_id,
            &risk_id,
            &dataset_commitment,
            &ai_system_id,
            &dataset_id,
            &model_version_id,
            log_path,
        )?
    {
        return Err(PolicyViolation::new(
            CODE_MISSING_HUMAN_APPROVAL_FOR_PROMOTION,
            "policy_violation: model_promoted requires prior human_approved decision=approve with matching assessment_id/risk_id/dataset_governance_commitment/ai_system_id/dataset_id/model_version_id and approved_human_event_id",
        ));
    }

    Ok(())
}

/* ------------------------- log helpers ------------------------- */

fn open_reader_if_exists(log_path: &str) -> Result<Option<BufReader<File>>, PolicyViolation> {
    match File::open(log_path) {
        Ok(f) => Ok(Some(BufReader::new(f))),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(PolicyViolation::new("io_error", e.to_string())),
    }
}

fn read_event(rec: StoredRecord) -> Result<EvidenceEvent, PolicyViolation> {
    serde_json::from_str::<EvidenceEvent>(&rec.event_json)
        .map_err(|e| PolicyViolation::new("log_parse_error", e.to_string()))
}

fn has_event_for_run(
    event_type: &str,
    run_id: &str,
    log_path: &str,
) -> Result<bool, PolicyViolation> {
    let Some(reader) = open_reader_if_exists(log_path)? else {
        return Ok(false);
    };

    for line in reader.lines() {
        let l = line.map_err(|e| PolicyViolation::new("io_error", e.to_string()))?;
        let t = l.trim();
        if t.is_empty() {
            continue;
        }

        let rec: StoredRecord = serde_json::from_str(t)
            .map_err(|e| PolicyViolation::new("log_parse_error", e.to_string()))?;
        let ev = read_event(rec)?;

        if ev.run_id == run_id && ev.event_type == event_type {
            return Ok(true);
        }
    }

    Ok(false)
}

fn has_passed_evaluation(run_id: &str, log_path: &str) -> Result<bool, PolicyViolation> {
    let Some(reader) = open_reader_if_exists(log_path)? else {
        return Ok(false);
    };

    for line in reader.lines() {
        let l = line.map_err(|e| PolicyViolation::new("io_error", e.to_string()))?;
        let t = l.trim();
        if t.is_empty() {
            continue;
        }

        let rec: StoredRecord = serde_json::from_str(t)
            .map_err(|e| PolicyViolation::new("log_parse_error", e.to_string()))?;
        let ev = read_event(rec)?;

        if ev.run_id != run_id {
            continue;
        }
        if ev.event_type != "evaluation_reported" {
            continue;
        }

        let passed = ev
            .payload
            .get("passed")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);

        if passed {
            return Ok(true);
        }
    }

    Ok(false)
}

fn has_risk_reviewed_approved(
    run_id: &str,
    assessment_id: &str,
    risk_id: &str,
    dataset_commitment: &str,
    ai_system_id: &str,
    dataset_id: &str,
    model_version_id: &str,
    log_path: &str,
) -> Result<bool, PolicyViolation> {
    let Some(reader) = open_reader_if_exists(log_path)? else {
        return Ok(false);
    };

    for line in reader.lines() {
        let l = line.map_err(|e| PolicyViolation::new("io_error", e.to_string()))?;
        let t = l.trim();
        if t.is_empty() {
            continue;
        }

        let rec: StoredRecord = serde_json::from_str(t)
            .map_err(|e| PolicyViolation::new("log_parse_error", e.to_string()))?;
        let ev = read_event(rec)?;

        if ev.run_id != run_id {
            continue;
        }
        if ev.event_type != "risk_reviewed" {
            continue;
        }

        let p = &ev.payload;
        let rid = p.get("risk_id").and_then(|v| v.as_str()).unwrap_or("");
        let aid = p
            .get("assessment_id")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let dgc = p
            .get("dataset_governance_commitment")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let ai = p.get("ai_system_id").and_then(|v| v.as_str()).unwrap_or("");
        let di = p.get("dataset_id").and_then(|v| v.as_str()).unwrap_or("");
        let mvi = p
            .get("model_version_id")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let decision = p.get("decision").and_then(|v| v.as_str()).unwrap_or("");

        if rid == risk_id
            && aid == assessment_id
            && dgc == dataset_commitment
            && ai == ai_system_id
            && di == dataset_id
            && mvi == model_version_id
            && decision == "approve"
        {
            return Ok(true);
        }
    }

    Ok(false)
}

fn human_approved_event_ok(
    run_id: &str,
    approved_human_event_id: &str,
    assessment_id: &str,
    risk_id: &str,
    dataset_commitment: &str,
    ai_system_id: &str,
    dataset_id: &str,
    model_version_id: &str,
    log_path: &str,
) -> Result<bool, PolicyViolation> {
    let Some(reader) = open_reader_if_exists(log_path)? else {
        return Ok(false);
    };

    for line in reader.lines() {
        let l = line.map_err(|e| PolicyViolation::new("io_error", e.to_string()))?;
        let t = l.trim();
        if t.is_empty() {
            continue;
        }

        let rec: StoredRecord = serde_json::from_str(t)
            .map_err(|e| PolicyViolation::new("log_parse_error", e.to_string()))?;
        let ev = read_event(rec)?;

        if ev.run_id != run_id {
            continue;
        }
        if ev.event_type != "human_approved" {
            continue;
        }
        if ev.event_id != approved_human_event_id {
            continue;
        }

        let p = &ev.payload;
        let scope_ok = p.get("scope").and_then(|v| v.as_str()).unwrap_or("") == "model_promoted";
        let decision_ok = p.get("decision").and_then(|v| v.as_str()).unwrap_or("") == "approve";
        let aid = p
            .get("assessment_id")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let rid = p.get("risk_id").and_then(|v| v.as_str()).unwrap_or("");
        let dgc = p
            .get("dataset_governance_commitment")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let ai = p.get("ai_system_id").and_then(|v| v.as_str()).unwrap_or("");
        let di = p.get("dataset_id").and_then(|v| v.as_str()).unwrap_or("");
        let mvi = p
            .get("model_version_id")
            .and_then(|v| v.as_str())
            .unwrap_or("");

        if scope_ok
            && decision_ok
            && aid == assessment_id
            && rid == risk_id
            && dgc == dataset_commitment
            && ai == ai_system_id
            && di == dataset_id
            && mvi == model_version_id
        {
            return Ok(true);
        }
    }

    Ok(false)
}

#[cfg(test)]
mod allowlist_tests {
    use super::*;
    use crate::policy_config::test_sync::APPROVER_ALLOWLIST_ENV_LOCK;
    use crate::policy_config::PolicyConfig;

    fn human_payload(approver: &str) -> serde_json::Value {
        serde_json::json!({
            "scope": "model_promoted",
            "decision": "approve",
            "approver": approver,
            "justification": "ok",
            "assessment_id": "a1",
            "risk_id": "r1",
            "dataset_governance_commitment": "c1",
            "ai_system_id": "ai1",
            "dataset_id": "d1",
            "model_version_id": "m1",
        })
    }

    fn human_ev(approver: &str) -> EvidenceEvent {
        EvidenceEvent {
            event_id: "h1".into(),
            event_type: "human_approved".into(),
            ts_utc: "t".into(),
            actor: "x".into(),
            system: "y".into(),
            run_id: "run".into(),
            environment: Some("dev".into()),
            payload: human_payload(approver),
        }
    }

    #[test]
    fn human_approver_rejected_when_allowlist_enforced() {
        let _g = APPROVER_ALLOWLIST_ENV_LOCK.lock().unwrap();
        std::env::remove_var("AIGOV_APPROVER_ALLOWLIST");
        let cfg = PolicyConfig {
            enforce_approver_allowlist: true,
            block_if_missing_evidence: false,
            require_risk_review_for_approval: false,
            ..PolicyConfig::default()
        };
        let e = human_ev("unknown_role");
        let err = enforce(&e, "noop", &cfg).unwrap_err();
        assert_eq!(err.code, CODE_APPROVER_NOT_ALLOWLISTED);
        assert!(!err.message.trim().is_empty());
    }

    #[test]
    fn human_approver_ok_when_allowlist_disabled() {
        let _g = APPROVER_ALLOWLIST_ENV_LOCK.lock().unwrap();
        std::env::remove_var("AIGOV_APPROVER_ALLOWLIST");
        let cfg = PolicyConfig {
            enforce_approver_allowlist: false,
            block_if_missing_evidence: false,
            require_risk_review_for_approval: false,
            ..PolicyConfig::default()
        };
        let e = human_ev("anyone");
        assert!(enforce(&e, "noop", &cfg).is_ok());
    }

    #[test]
    fn human_approver_respects_configured_allowlist() {
        let _g = APPROVER_ALLOWLIST_ENV_LOCK.lock().unwrap();
        std::env::remove_var("AIGOV_APPROVER_ALLOWLIST");
        let cfg = PolicyConfig {
            enforce_approver_allowlist: true,
            block_if_missing_evidence: false,
            require_risk_review_for_approval: false,
            approver_allowlist: vec!["release_manager".to_string()],
            ..PolicyConfig::default()
        };
        assert!(enforce(&human_ev("release_manager"), "noop", &cfg).is_ok());
        let err = enforce(&human_ev("compliance_officer"), "noop", &cfg).unwrap_err();
        assert_eq!(err.code, CODE_APPROVER_NOT_ALLOWLISTED);
    }

    #[test]
    fn human_approver_allowlist_env_overrides_config() {
        let _g = APPROVER_ALLOWLIST_ENV_LOCK.lock().unwrap();
        std::env::set_var("AIGOV_APPROVER_ALLOWLIST", "env_approver");
        let cfg = PolicyConfig {
            enforce_approver_allowlist: true,
            block_if_missing_evidence: false,
            require_risk_review_for_approval: false,
            approver_allowlist: vec!["only_on_file".to_string()],
            ..PolicyConfig::default()
        };
        assert!(enforce(&human_ev("env_approver"), "noop", &cfg).is_ok());
        let err = enforce(&human_ev("only_on_file"), "noop", &cfg).unwrap_err();
        assert_eq!(err.code, CODE_APPROVER_NOT_ALLOWLISTED);
        std::env::remove_var("AIGOV_APPROVER_ALLOWLIST");
    }
}

#[cfg(test)]
mod gate_tests {
    use super::*;
    use crate::audit_store::StoredRecord;
    use crate::policy_config::PolicyConfig;
    use crate::schema::EvidenceEvent;

    fn model_trained_ev() -> EvidenceEvent {
        EvidenceEvent {
            event_id: "m1".into(),
            event_type: "model_trained".into(),
            ts_utc: "t".into(),
            actor: "x".into(),
            system: "y".into(),
            run_id: "run1".into(),
            environment: None,
            payload: serde_json::json!({
                "ai_system_id": "ai1",
                "dataset_id": "d1",
                "model_version_id": "mv1",
            }),
        }
    }

    #[test]
    fn model_trained_requires_data_registered_when_evidence_gating_on() {
        let cfg = PolicyConfig {
            block_if_missing_evidence: true,
            ..PolicyConfig::default()
        };
        let dir = tempfile::TempDir::new().unwrap();
        let log = dir.path().join("empty.jsonl");
        let err = enforce(&model_trained_ev(), log.to_str().unwrap(), &cfg).unwrap_err();
        assert_eq!(err.code, CODE_MISSING_DATA_REGISTERED);
        assert!(!err.message.trim().is_empty());
    }

    #[test]
    fn model_trained_skips_data_registered_when_evidence_gating_off() {
        let cfg = PolicyConfig {
            block_if_missing_evidence: false,
            ..PolicyConfig::default()
        };
        let dir = tempfile::TempDir::new().unwrap();
        let log = dir.path().join("empty.jsonl");
        assert!(enforce(&model_trained_ev(), log.to_str().unwrap(), &cfg).is_ok());
    }

    fn model_promoted_ev() -> EvidenceEvent {
        EvidenceEvent {
            event_id: "p1".into(),
            event_type: "model_promoted".into(),
            ts_utc: "t".into(),
            actor: "x".into(),
            system: "y".into(),
            run_id: "run1".into(),
            environment: None,
            payload: serde_json::json!({
                "artifact_path": "s3://bucket/model",
                "artifact_sha256": "11".repeat(32),
                "promotion_reason": "metrics ok",
                "assessment_id": "a1",
                "risk_id": "r1",
                "dataset_governance_commitment": "c1",
                "ai_system_id": "ai1",
                "dataset_id": "d1",
                "model_version_id": "mv1",
            }),
        }
    }

    #[test]
    fn model_promoted_rejected_when_artifact_digest_missing() {
        let cfg = PolicyConfig::default();
        let dir = tempfile::TempDir::new().unwrap();
        let log = dir.path().join("empty.jsonl");
        let mut ev = model_promoted_ev();
        if let Some(obj) = ev.payload.as_object_mut() {
            obj.remove("artifact_sha256");
        }
        let err = enforce(&ev, log.to_str().unwrap(), &cfg).unwrap_err();
        assert_eq!(err.code, CODE_SCHEMA_INVALID);
        assert!(!err.message.trim().is_empty());
    }

    fn human_approved_ev() -> EvidenceEvent {
        EvidenceEvent {
            event_id: "h1".into(),
            event_type: "human_approved".into(),
            ts_utc: "t".into(),
            actor: "x".into(),
            system: "y".into(),
            run_id: "run1".into(),
            environment: None,
            payload: serde_json::json!({
                "scope": "model_promoted",
                "decision": "approve",
                "approver": "compliance_officer",
                "justification": "ok",
                "assessment_id": "a1",
                "risk_id": "r1",
                "dataset_governance_commitment": "c1",
                "ai_system_id": "ai1",
                "dataset_id": "d1",
                "model_version_id": "mv1",
            }),
        }
    }

    #[test]
    fn default_policy_blocks_model_promoted_without_evaluation() {
        let cfg = PolicyConfig {
            require_approval: false,
            ..PolicyConfig::default()
        };
        let dir = tempfile::TempDir::new().unwrap();
        let log = dir.path().join("empty.jsonl");
        std::fs::write(&log, "").unwrap();
        let err = enforce(&model_promoted_ev(), log.to_str().unwrap(), &cfg).unwrap_err();
        assert_eq!(err.code, CODE_MISSING_PASSED_EVALUATION_FOR_PROMOTION);
        assert!(!err.message.trim().is_empty());
    }

    #[test]
    fn model_promoted_skips_evaluation_gate_when_flag_off() {
        let cfg = PolicyConfig {
            require_approval: false,
            require_passed_evaluation_for_promotion: false,
            ..PolicyConfig::default()
        };
        let dir = tempfile::TempDir::new().unwrap();
        let log = dir.path().join("empty.jsonl");
        std::fs::write(&log, "").unwrap();
        let err = enforce(&model_promoted_ev(), log.to_str().unwrap(), &cfg).unwrap_err();
        assert_eq!(err.code, CODE_MISSING_RISK_REVIEW_FOR_PROMOTION);
        assert!(!err.message.trim().is_empty());
    }

    #[test]
    fn model_promoted_succeeds_without_chain_when_promotion_gates_off() {
        let cfg = PolicyConfig {
            require_approval: false,
            require_passed_evaluation_for_promotion: false,
            require_risk_review_for_promotion: false,
            ..PolicyConfig::default()
        };
        let dir = tempfile::TempDir::new().unwrap();
        let log = dir.path().join("empty.jsonl");
        std::fs::write(&log, "").unwrap();
        assert!(enforce(&model_promoted_ev(), log.to_str().unwrap(), &cfg).is_ok());
    }

    #[test]
    fn human_approved_requires_prior_risk_review_by_default() {
        let cfg = PolicyConfig {
            enforce_approver_allowlist: false,
            ..PolicyConfig::default()
        };
        let dir = tempfile::TempDir::new().unwrap();
        let log = dir.path().join("empty.jsonl");
        std::fs::write(&log, "").unwrap();
        let err = enforce(&human_approved_ev(), log.to_str().unwrap(), &cfg).unwrap_err();
        assert_eq!(err.code, CODE_MISSING_RISK_REVIEW_FOR_APPROVAL);
        assert!(!err.message.trim().is_empty());
    }

    #[test]
    fn human_approved_skips_risk_review_when_flag_off() {
        let cfg = PolicyConfig {
            enforce_approver_allowlist: false,
            require_risk_review_for_approval: false,
            ..PolicyConfig::default()
        };
        let dir = tempfile::TempDir::new().unwrap();
        let log = dir.path().join("empty.jsonl");
        std::fs::write(&log, "").unwrap();
        assert!(enforce(&human_approved_ev(), log.to_str().unwrap(), &cfg).is_ok());
    }

    #[test]
    fn model_promoted_skips_risk_gate_when_off_after_passed_evaluation_in_log() {
        let eval_ev = EvidenceEvent {
            event_id: "e1".into(),
            event_type: "evaluation_reported".into(),
            ts_utc: "t".into(),
            actor: "x".into(),
            system: "y".into(),
            run_id: "run1".into(),
            environment: None,
            payload: serde_json::json!({
                "ai_system_id": "ai1",
                "dataset_id": "d1",
                "model_version_id": "mv1",
                "metric": "acc",
                "value": 0.9,
                "threshold": 0.8,
                "passed": true,
            }),
        };
        let dir = tempfile::TempDir::new().unwrap();
        let log = dir.path().join("log.jsonl");
        let rec = StoredRecord {
            prev_hash: "GENESIS".into(),
            record_hash: "h1".into(),
            event_json: serde_json::to_string(&eval_ev).unwrap(),
        };
        std::fs::write(&log, format!("{}\n", serde_json::to_string(&rec).unwrap())).unwrap();

        let cfg = PolicyConfig {
            require_approval: false,
            require_risk_review_for_promotion: false,
            ..PolicyConfig::default()
        };
        assert!(enforce(&model_promoted_ev(), log.to_str().unwrap(), &cfg).is_ok());
    }
}
