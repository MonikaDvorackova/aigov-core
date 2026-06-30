//! Trace verification plan documents for audit export epistemic review.
//!
//! Schema: `govai.standards.trace_verification_plan.v1`

use crate::canonical_json::{sort_json_value, sha256_hex_bytes};
use crate::epistemic_readiness::{EpistemicReadiness, KnowledgeRequirement};
use serde::Serialize;
use serde_json::{json, Value};

pub const TRACE_VERIFICATION_PLAN_SCHEMA_V1: &str = "govai.standards.trace_verification_plan.v1";

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct TraceVerificationRequirement {
    pub requirement_id: String,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct TraceVerificationFinding {
    pub finding_id: String,
    pub requirement_id: String,
    /// `PASS` | `WARN` | `FAIL` | `NOT_APPLICABLE`
    pub status: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct TraceVerificationPlan {
    pub schema_version: String,
    pub trace_id: String,
    pub tenant_scope: String,
    pub requirements: Vec<TraceVerificationRequirement>,
    pub findings: Vec<TraceVerificationFinding>,
    pub plan_digest: String,
}

pub fn build_trace_verification_plan_from_readiness(
    export: &Value,
    readiness: &EpistemicReadiness,
    requirements: &[KnowledgeRequirement],
) -> TraceVerificationPlan {
    let trace_id = if readiness.decision_knowledge.run_id.is_empty() {
        export
            .get("run")
            .and_then(|r| r.get("run_id"))
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
            .unwrap_or_else(|| "unknown".to_string())
    } else {
        readiness.decision_knowledge.run_id.clone()
    };

    let tenant_scope = export
        .get("tenant")
        .and_then(|t| t.get("ledger_tenant_id"))
        .and_then(|v| v.as_str())
        .or_else(|| {
            export
                .get("tenant")
                .and_then(|t| t.get("billing_tenant_id"))
                .and_then(|v| v.as_str())
        })
        .unwrap_or("unknown")
        .to_string();

    let mut reqs: Vec<TraceVerificationRequirement> = requirements
        .iter()
        .map(|r| TraceVerificationRequirement {
            requirement_id: format!("req.{}", r.code),
            description: r.detail.clone(),
        })
        .collect();
    reqs.sort_by(|a, b| a.requirement_id.cmp(&b.requirement_id));

    let mut findings: Vec<TraceVerificationFinding> = requirements
        .iter()
        .enumerate()
        .map(|(i, r)| TraceVerificationFinding {
            finding_id: format!("finding.{:03}", i + 1),
            requirement_id: format!("req.{}", r.code),
            status: if r.satisfied {
                "PASS".to_string()
            } else if r.category == "coverage" || r.code == "missing_policy_artifact" {
                "WARN".to_string()
            } else {
                "FAIL".to_string()
            },
        })
        .collect();
    findings.sort_by(|a, b| a.finding_id.cmp(&b.finding_id));

    let mut plan = TraceVerificationPlan {
        schema_version: TRACE_VERIFICATION_PLAN_SCHEMA_V1.to_string(),
        trace_id,
        tenant_scope,
        requirements: reqs,
        findings,
        plan_digest: String::new(),
    };
    plan.plan_digest = digest_trace_verification_plan(&plan);
    plan
}

pub fn digest_trace_verification_plan(plan: &TraceVerificationPlan) -> String {
    let preimage = canonical_trace_plan_preimage(plan);
    let sorted = sort_json_value(preimage);
    let bytes = serde_json::to_vec(&sorted).expect("trace plan preimage serializes");
    format!("sha256:{}", sha256_hex_bytes(&bytes))
}

fn canonical_trace_plan_preimage(plan: &TraceVerificationPlan) -> Value {
    let mut reqs: Vec<Value> = plan
        .requirements
        .iter()
        .map(|r| {
            json!({
                "description": r.description,
                "requirement_id": r.requirement_id,
            })
        })
        .collect();
    reqs.sort_by(|a, b| {
        a.get("requirement_id")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .cmp(b.get("requirement_id").and_then(|v| v.as_str()).unwrap_or(""))
    });

    let mut fins: Vec<Value> = plan
        .findings
        .iter()
        .map(|f| {
            json!({
                "finding_id": f.finding_id,
                "requirement_id": f.requirement_id,
                "status": f.status,
            })
        })
        .collect();
    fins.sort_by(|a, b| {
        a.get("finding_id")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .cmp(b.get("finding_id").and_then(|v| v.as_str()).unwrap_or(""))
    });

    json!({
        "findings": fins,
        "requirements": reqs,
        "schema_version": plan.schema_version,
        "tenant_scope": plan.tenant_scope,
        "trace_id": plan.trace_id,
    })
}

pub fn trace_verification_plan_to_json(plan: &TraceVerificationPlan) -> Value {
    let mut v = serde_json::to_value(plan).expect("TraceVerificationPlan serializes");
    if let Some(obj) = v.as_object_mut() {
        obj.insert(
            "plan_digest".to_string(),
            Value::String(plan.plan_digest.clone()),
        );
    }
    v
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::epistemic_readiness::{
        evaluate_epistemic_readiness_from_export, EpistemicReadinessOptions,
    };
    use crate::policy_config::PolicyConfig;
    use crate::replay_validation::EXPORT_SCHEMA_V1;
    use serde_json::json;

    #[test]
    fn plan_digest_is_deterministic() {
        let export = json!({
            "schema_version": EXPORT_SCHEMA_V1,
            "policy_version": "p1",
            "run": { "run_id": "run-1" },
            "tenant": { "ledger_tenant_id": "tenant-1" },
            "decision": { "verdict": "BLOCKED" },
            "evidence_events": [],
            "evidence_hashes": { "events_content_sha256": "0".repeat(64), "log_chain": [] },
        });
        let cfg = PolicyConfig::default();
        let readiness = evaluate_epistemic_readiness_from_export(
            &export,
            &EpistemicReadinessOptions::offline(&cfg),
        );
        let reqs = vec![crate::epistemic_readiness::KnowledgeRequirement {
            code: "replay_validation_failure".to_string(),
            category: "replay".to_string(),
            satisfied: false,
            detail: "test".to_string(),
        }];
        let p1 = build_trace_verification_plan_from_readiness(&export, &readiness, &reqs);
        let p2 = build_trace_verification_plan_from_readiness(&export, &readiness, &reqs);
        assert_eq!(p1.plan_digest, p2.plan_digest);
        assert!(p1.plan_digest.starts_with("sha256:"));
    }
}
