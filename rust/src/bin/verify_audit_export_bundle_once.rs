//! Offline helper: verify a signed audit export zip bundle.
//! Usage: `verify_audit_export_bundle_once [--json] <bundle.zip>`

use aigov_audit::audit_export_verification::{
    verification_result_to_json, verify_audit_export_bundle_bytes, VerifyAuditExportBundleOptions,
};
use aigov_audit::policy_signing::load_trust_store_from_env;

fn main() {
    let mut args: Vec<String> = std::env::args().skip(1).collect();
    let json_mode = args.iter().any(|a| a == "--json");
    args.retain(|a| a != "--json");
    let expected_issuer = args
        .iter()
        .position(|a| a == "--expected-issuer-id")
        .and_then(|i| args.get(i + 1).cloned());
    args.retain(|a| a != "--expected-issuer-id");
    if let Some(ref id) = expected_issuer {
        args.retain(|a| a != id);
    }

    let path = args.first().unwrap_or_else(|| {
        eprintln!(
            "usage: verify_audit_export_bundle_once [--json] [--expected-issuer-id ISSUER] <bundle.zip>"
        );
        std::process::exit(2);
    });

    let zip_bytes = std::fs::read(path).unwrap_or_else(|e| {
        eprintln!("read {path}: {e}");
        std::process::exit(1);
    });

    let trust = load_trust_store_from_env().unwrap_or_else(|e| {
        eprintln!("trust store: {e}");
        std::process::exit(1);
    });

    let result = verify_audit_export_bundle_bytes(
        &zip_bytes,
        VerifyAuditExportBundleOptions {
            trust: &trust,
            expected_issuer_id: expected_issuer.as_deref(),
            policy_cfg: None,
        },
    );

    let out = verification_result_to_json(&result);
    if json_mode {
        println!("{}", serde_json::to_string_pretty(&out).expect("json"));
    } else {
        println!("overall_status={}", result.overall_status);
        println!(
            "canonical_bundle_digest_verified={}",
            result.canonical_bundle_digest_verified
        );
        println!("signature_verified={}", result.signature_verified);
        println!("schema_version_supported={}", result.schema_version_supported);
        println!("manifest_complete={}", result.manifest_complete);
        println!(
            "all_manifest_hashes_match={}",
            result.all_manifest_hashes_match
        );
        println!(
            "all_evidence_references_resolve={}",
            result.all_evidence_references_resolve
        );
        println!(
            "replay_validation_passed={}",
            result.replay_validation_passed
        );
        println!(
            "unsigned_dependency_detected={}",
            result.unsigned_dependency_detected
        );
        if !result.failures.is_empty() {
            println!("failures:");
            for f in &result.failures {
                println!("  - [{}] {}: {}", f.stage, f.code, f.message);
            }
        }
    }

    if result.overall_status != "success" {
        std::process::exit(1);
    }
}
