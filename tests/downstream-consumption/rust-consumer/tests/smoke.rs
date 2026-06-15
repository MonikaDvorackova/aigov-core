//! Downstream consumption smoke: compile and call public `aigov_audit` APIs from an external crate.

use aigov_audit::audit_export_verification::{
    verify_audit_export_bundle_bytes, VerifyAuditExportBundleOptions,
};
use aigov_audit::policy::enforce;
use aigov_audit::policy_config::PolicyConfig;
use aigov_audit::policy_signing::load_trust_store_from_env;
use aigov_audit::replay_validation::EXPORT_SCHEMA_V1;
use aigov_audit::schema::EvidenceEvent;
use std::path::PathBuf;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../..")
        .canonicalize()
        .expect("repo root")
}

#[test]
fn verifier_api_smoke() {
    let trust_json = std::fs::read_to_string(
        repo_root().join("examples/signed-audit-export-bundle/trust-demo.json"),
    )
    .expect("trust-demo.json");
    // SAFETY: single-threaded test; no concurrent env mutation.
    unsafe {
        std::env::set_var("AIGOV_POLICY_TRUST_ED25519_JSON", &trust_json);
    }
    let trust = load_trust_store_from_env().expect("trust store");
    let zip = std::fs::read(
        repo_root().join("examples/signed-audit-export-bundle/demo.valid.zip"),
    )
    .expect("demo.valid.zip");
    let policy = PolicyConfig::default();
    let result = verify_audit_export_bundle_bytes(
        &zip,
        VerifyAuditExportBundleOptions {
            trust: &trust,
            expected_issuer_id: None,
            policy_cfg: Some(&policy),
        },
    );
    assert_eq!(result.overall_status, "success");
    assert!(result.signature_verified);
    assert!(result.replay_validation_passed);
}

#[test]
fn policy_api_smoke() {
    let event = EvidenceEvent {
        event_id: "evt-downstream-smoke".into(),
        event_type: "ai_discovery_reported".into(),
        ts_utc: "2026-01-01T00:00:00Z".into(),
        actor: "downstream-smoke".into(),
        system: "rust-consumer".into(),
        run_id: "run-downstream-smoke".into(),
        environment: None,
        payload: serde_json::json!({}),
        parent_run_id: None,
        root_run_id: None,
        delegated_from_event_id: None,
        agent_id: None,
        agent_role: None,
        delegation_reason: None,
    };
    enforce(&event, "/dev/null", &PolicyConfig::default()).expect("policy enforce");
}

#[test]
fn audit_export_api_smoke() {
    assert_eq!(EXPORT_SCHEMA_V1, "aigov.audit_export.v1");
}
