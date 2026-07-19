use aigov_audit::policy::enforce;
use aigov_audit::policy_config::PolicyConfig;
use aigov_audit::schema::EvidenceEvent;

fn main() {
    println!("--- GovAI Core Minimal Project: Running Policy Engine ---\n");

    // 1. Setup global active policy configuration
    let cfg = PolicyConfig {
        enforce_approver_allowlist: false,
        block_if_missing_evidence: true,
        require_passed_evaluation_for_promotion: true,
        require_risk_review_for_promotion: true,
        require_approval: true,
        require_risk_review_for_approval: false,
        approver_allowlist: vec![],
    };

    // =========================================================================
    // CASE A: EVALUATING AN INVALID EVENT
    // =========================================================================
    let broken_payload = serde_json::json!({
        "ai_system_id": "sys-alpha-99",
        "dataset_id": "dataset-v1"
    });

    let broken_event = EvidenceEvent {
        event_id: "evt-001".to_string(),
        event_type: "data_registered".to_string(),
        ts_utc: "2026-07-01T16:50:00Z".to_string(),
        actor: "automation-pipeline".to_string(),
        system: "ci-cd-worker".to_string(),
        run_id: "run-xyz-123".to_string(),
        environment: Some("staging".to_string()),
        payload: broken_payload,
        parent_run_id: None,
        root_run_id: None,
        delegated_from_event_id: None,
        agent_id: None,
        agent_role: None,
        delegation_reason: None,
    };

    println!("Executing Evaluation A (Intentionally Incomplete Payload)...");
    match enforce(&broken_event, "dummy_audit.log", &cfg) {
        Ok(()) => println!("Result A: Success!"),
        Err(violation) => println!("Result A -> Caught Expected Violation: [{}]", violation.code),
    }

    println!("\n-------------------------------------------------------------\n");

    // =========================================================================
    // CASE B: EVALUATING A FULLY COMPLIANT EVENT
    // =========================================================================
    // We add all the metadata keys that enforce_data_registered mandates
    let compliant_payload = serde_json::json!({
        "ai_system_id": "sys-alpha-99",
        "dataset_id": "dataset-v1",
        "dataset": "customer_churn_records_2026",
        "dataset_fingerprint": "sha256-e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "dataset_governance_id": "gov-doc-churn-04",
        "dataset_governance_commitment": "eu-ai-act-compliance-level-3",
        "dataset_version": "v2.1.0",
        "source": "internal-production-replica-db",
        "intended_use": "training-predictive-retention-models",
        "limitations": "excludes-anonymized-historical-geographic-profiles",
        "quality_summary": "passed-null-checks-and-cardinality-thresholds",
        "governance_status": "certified-by-data-office"
    });

    let compliant_event = EvidenceEvent {
        event_id: "evt-002".to_string(),
        event_type: "data_registered".to_string(),
        ts_utc: "2026-07-01T17:00:00Z".to_string(),
        actor: "data-governance-daemon".to_string(),
        system: "data-warehouse-pipeline".to_string(),
        run_id: "run-xyz-123".to_string(),
        environment: Some("production".to_string()),
        payload: compliant_payload,
        parent_run_id: None,
        root_run_id: None,
        delegated_from_event_id: None,
        agent_id: None,
        agent_role: None,
        delegation_reason: None,
    };

    println!("Executing Evaluation B (Fully Compliant Governance Payload)...");
    match enforce(&compliant_event, "dummy_audit.log", &cfg) {
        Ok(()) => {
            println!("Result B -> [VERIFICATION SUCCESSFUL]");
            println!("Message: The event adheres perfectly to active corporate governance rules!");
        },
        Err(violation) => println!("Result B -> Unexpected Violation: {}", violation.message),
    }
}