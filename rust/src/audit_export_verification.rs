//! Structured offline verification for signed audit export zip bundles.

use crate::audit_export_bundle::{
    parse_manifest_bytes, read_zip_entries, sha256_content_hex, AuditExportBundleManifest,
    BUNDLE_SCHEMA_V1, DEFAULT_MANIFEST_PATH,
};
use crate::audit_export_signing::{
    validate_signed_audit_export_integrity, verify_audit_export_ed25519_signature,
};
use crate::policy_config::PolicyConfig;
use crate::policy_signing::PolicyTrustStore;
use crate::replay_engine::replay_audit_export_v1;
use crate::replay_validation::EXPORT_SCHEMA_V1;
use serde::Serialize;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct VerificationFailure {
    pub code: String,
    pub message: String,
    pub stage: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum OverallVerificationStatus {
    Success,
    SignatureInvalid,
    BundleTampered,
    MissingEvidence,
    UnsupportedSchemaVersion,
    HashMismatch,
    ReplayValidationFailure,
    IncompleteManifest,
}

impl OverallVerificationStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Success => "success",
            Self::SignatureInvalid => "signature_invalid",
            Self::BundleTampered => "bundle_tampered",
            Self::MissingEvidence => "missing_evidence",
            Self::UnsupportedSchemaVersion => "unsupported_schema_version",
            Self::HashMismatch => "hash_mismatch",
            Self::ReplayValidationFailure => "replay_validation_failure",
            Self::IncompleteManifest => "incomplete_manifest",
        }
    }
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct AuditExportVerificationResult {
    pub canonical_bundle_digest_verified: bool,
    pub signature_verified: bool,
    pub schema_version_supported: bool,
    pub manifest_complete: bool,
    pub all_manifest_hashes_match: bool,
    pub all_evidence_references_resolve: bool,
    pub replay_validation_passed: bool,
    pub unsigned_dependency_detected: bool,
    pub overall_status: String,
    pub failures: Vec<VerificationFailure>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub run_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub export_schema_version: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bundle_schema_version: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub signature_issuer_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub replay_ok: Option<bool>,
}

impl AuditExportVerificationResult {
    fn new() -> Self {
        Self {
            canonical_bundle_digest_verified: false,
            signature_verified: false,
            schema_version_supported: false,
            manifest_complete: false,
            all_manifest_hashes_match: false,
            all_evidence_references_resolve: false,
            replay_validation_passed: false,
            unsigned_dependency_detected: false,
            overall_status: OverallVerificationStatus::IncompleteManifest.as_str().to_string(),
            failures: Vec::new(),
            run_id: None,
            export_schema_version: None,
            bundle_schema_version: None,
            signature_issuer_id: None,
            replay_ok: None,
        }
    }

    fn push_failure(&mut self, stage: &str, code: &str, message: impl Into<String>) {
        self.failures.push(VerificationFailure {
            code: code.to_string(),
            message: message.into(),
            stage: stage.to_string(),
        });
    }

    fn finalize_status(&mut self) {
        self.overall_status = if self.failures.is_empty()
            && self.canonical_bundle_digest_verified
            && self.signature_verified
            && self.schema_version_supported
            && self.manifest_complete
            && self.all_manifest_hashes_match
            && self.all_evidence_references_resolve
            && self.replay_validation_passed
            && !self.unsigned_dependency_detected
        {
            OverallVerificationStatus::Success.as_str().to_string()
        } else {
            derive_overall_status(self).as_str().to_string()
        };
    }
}

fn derive_overall_status(result: &AuditExportVerificationResult) -> OverallVerificationStatus {
    for f in &result.failures {
        match f.code.as_str() {
            "unsupported_bundle_schema" | "unsupported_export_schema" => {
                return OverallVerificationStatus::UnsupportedSchemaVersion;
            }
            "canonical_bundle_digest_mismatch" | "zip_tampered" => {
                return OverallVerificationStatus::BundleTampered;
            }
            "manifest_file_hash_mismatch" | "export_hash_mismatch" | "events_content_sha256_mismatch"
            | "bundle_sha256_mismatch" => {
                return OverallVerificationStatus::HashMismatch;
            }
            "missing_manifest_file" | "missing_evidence_ref" | "missing_finding_ref"
            | "missing_required_file" | "missing_unsigned_dependency" => {
                return OverallVerificationStatus::MissingEvidence;
            }
            "signature_invalid" | "export_unsigned" | "issuer_mismatch" => {
                return OverallVerificationStatus::SignatureInvalid;
            }
            "replay_validation_failed" | "replay_verdict_mismatch" => {
                return OverallVerificationStatus::ReplayValidationFailure;
            }
            "manifest_incomplete" | "manifest_missing" | "audit_export_missing" => {
                return OverallVerificationStatus::IncompleteManifest;
            }
            _ => {}
        }
    }
    if !result.signature_verified {
        return OverallVerificationStatus::SignatureInvalid;
    }
    if !result.all_manifest_hashes_match || !result.canonical_bundle_digest_verified {
        return OverallVerificationStatus::BundleTampered;
    }
    if !result.manifest_complete
        || !result.all_evidence_references_resolve
        || result.unsigned_dependency_detected
    {
        return OverallVerificationStatus::MissingEvidence;
    }
    if !result.replay_validation_passed {
        return OverallVerificationStatus::ReplayValidationFailure;
    }
    OverallVerificationStatus::IncompleteManifest
}

pub struct VerifyAuditExportBundleOptions<'a> {
    pub trust: &'a PolicyTrustStore,
    pub expected_issuer_id: Option<&'a str>,
    pub policy_cfg: Option<&'a PolicyConfig>,
}

pub fn verify_audit_export_bundle_bytes(
    zip_bytes: &[u8],
    opts: VerifyAuditExportBundleOptions<'_>,
) -> AuditExportVerificationResult {
    let mut result = AuditExportVerificationResult::new();
    let default_policy = PolicyConfig::default();
    let policy_cfg = opts.policy_cfg.unwrap_or(&default_policy);

    let entries = match read_zip_entries(zip_bytes) {
        Ok(e) => e,
        Err(e) => {
            result.push_failure("bundle", "zip_invalid", e);
            result.finalize_status();
            return result;
        }
    };

    let manifest_bytes = match entries.get(DEFAULT_MANIFEST_PATH) {
        Some(b) => b.clone(),
        None => {
            result.push_failure(
                "manifest",
                "manifest_missing",
                format!("missing required file {DEFAULT_MANIFEST_PATH}"),
            );
            result.finalize_status();
            return result;
        }
    };

    let manifest = match parse_manifest_bytes(&manifest_bytes) {
        Ok(m) => m,
        Err(e) => {
            result.push_failure("manifest", "manifest_parse_error", e);
            result.finalize_status();
            return result;
        }
    };

    result.run_id = Some(manifest.run_id.clone());
    result.bundle_schema_version = Some(manifest.schema_version.clone());

    if manifest.schema_version != BUNDLE_SCHEMA_V1 {
        result.push_failure(
            "manifest",
            "unsupported_bundle_schema",
            format!(
                "expected {BUNDLE_SCHEMA_V1}, got {}",
                manifest.schema_version
            ),
        );
    } else {
        result.schema_version_supported = true;
    }

    let recomputed = crate::audit_export_bundle::compute_canonical_bundle_digest(&manifest);
    if recomputed != manifest.canonical_bundle_digest_sha256.trim().to_ascii_lowercase() {
        result.push_failure(
            "manifest",
            "canonical_bundle_digest_mismatch",
            "manifest canonical_bundle_digest_sha256 does not match recomputed digest",
        );
    } else {
        result.canonical_bundle_digest_verified = true;
    }

    verify_manifest_files(&manifest, &entries, &mut result);
    verify_reference_paths(&manifest, &entries, &mut result);
    verify_unsigned_dependencies(&manifest, &entries, &mut result);

    let export_path = manifest.audit_export_path.trim();
    let export_bytes = match entries.get(export_path) {
        Some(b) => b,
        None => {
            result.push_failure(
                "export",
                "audit_export_missing",
                format!("audit export file missing at {export_path}"),
            );
            result.finalize_status();
            return result;
        }
    };

    let export: Value = match serde_json::from_slice(export_bytes) {
        Ok(v) => v,
        Err(e) => {
            result.push_failure("export", "audit_export_parse_error", format!("{e}"));
            result.finalize_status();
            return result;
        }
    };

    result.export_schema_version = export
        .get("schema_version")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    if export
        .get("schema_version")
        .and_then(|v| v.as_str())
        != Some(EXPORT_SCHEMA_V1)
    {
        result.schema_version_supported = false;
        result.push_failure(
            "export",
            "unsupported_export_schema",
            format!("expected {EXPORT_SCHEMA_V1}"),
        );
    }

    match validate_signed_audit_export_integrity(&export) {
        Ok(_) => {}
        Err(e) => {
            let code = if e.contains("events_content_sha256 mismatch") {
                "events_content_sha256_mismatch"
            } else if e.contains("unsupported export schema") {
                "unsupported_export_schema"
            } else if e.contains("bundle_sha256") {
                "bundle_sha256_mismatch"
            } else {
                "export_hash_mismatch"
            };
            result.push_failure("export", code, e);
        }
    }

    match verify_audit_export_ed25519_signature(&export, opts.trust, opts.expected_issuer_id) {
        Ok(issuer) => {
            result.signature_verified = true;
            result.signature_issuer_id = Some(issuer);
        }
        Err(e) => {
            let code = if e.contains("unsigned") {
                "export_unsigned"
            } else if e.contains("issuer_id") && opts.expected_issuer_id.is_some() {
                "issuer_mismatch"
            } else {
                "signature_invalid"
            };
            result.push_failure("signature", code, e);
        }
    }

    let replay = replay_audit_export_v1(&export, policy_cfg);
    result.replay_ok = Some(replay.ok);
    if replay.validation.is_ok() && replay.ok {
        result.replay_validation_passed = true;
    } else {
        if !replay.validation.is_ok() {
            for err in &replay.validation.errors {
                result.push_failure(
                    "replay",
                    "replay_validation_failed",
                    format!("{}: {}", err.code, err.message),
                );
            }
        }
        if !replay.ok {
            result.push_failure(
                "replay",
                "replay_verdict_mismatch",
                format!(
                    "exported_verdict={:?} reconstructed_verdict={}",
                    replay.exported_verdict, replay.reconstructed_verdict
                ),
            );
        }
    }

    result.finalize_status();
    result
}

fn verify_manifest_files(
    manifest: &AuditExportBundleManifest,
    entries: &BTreeMap<String, Vec<u8>>,
    result: &mut AuditExportVerificationResult,
) {
    let mut required_paths: BTreeSet<String> = BTreeSet::new();
    let mut all_hashes_ok = true;
    let mut all_required_present = true;

    for file in &manifest.files {
        required_paths.insert(file.path.clone());
        let present = entries.get(&file.path);
        if file.required && present.is_none() {
            all_required_present = false;
            result.push_failure(
                "manifest",
                "missing_required_file",
                format!("required manifest file missing: {}", file.path),
            );
            continue;
        }
        let Some(content) = present else {
            continue;
        };
        let actual = sha256_content_hex(content);
        if actual != file.sha256.trim().to_ascii_lowercase() {
            all_hashes_ok = false;
            result.push_failure(
                "manifest",
                "manifest_file_hash_mismatch",
                format!("hash mismatch for {}", file.path),
            );
        }
    }

    for path in entries.keys() {
        if path == DEFAULT_MANIFEST_PATH {
            continue;
        }
        if !required_paths.contains(path) && !path.starts_with("__MACOSX/") {
            // Extra files are allowed; unsigned_dependency check handles required explanations.
            let _ = path;
        }
    }

    if all_required_present && !manifest.files.is_empty() {
        result.manifest_complete = true;
    } else if manifest.files.is_empty() {
        result.push_failure("manifest", "manifest_incomplete", "manifest.files is empty");
    }

    result.all_manifest_hashes_match = all_hashes_ok && all_required_present;
}

fn verify_reference_paths(
    manifest: &AuditExportBundleManifest,
    entries: &BTreeMap<String, Vec<u8>>,
    result: &mut AuditExportVerificationResult,
) {
    let mut evidence_ok = true;

    for ev in &manifest.evidence_refs {
        if !entries.contains_key(&ev.path) {
            evidence_ok = false;
            result.push_failure(
                "references",
                "missing_evidence_ref",
                format!("evidence ref {} -> missing path {}", ev.ref_id, ev.path),
            );
        }
    }
    for fr in &manifest.finding_refs {
        if !entries.contains_key(&fr.path) {
            evidence_ok = false;
            result.push_failure(
                "references",
                "missing_finding_ref",
                format!(
                    "finding ref {} -> missing path {}",
                    fr.finding_id, fr.path
                ),
            );
        }
    }

    result.all_evidence_references_resolve = evidence_ok;
}

fn verify_unsigned_dependencies(
    manifest: &AuditExportBundleManifest,
    entries: &BTreeMap<String, Vec<u8>>,
    result: &mut AuditExportVerificationResult,
) {
    for dep in &manifest.unsigned_dependencies {
        if dep.required_for_explanation && !entries.contains_key(&dep.path) {
            result.unsigned_dependency_detected = true;
            result.push_failure(
                "unsigned",
                "missing_unsigned_dependency",
                format!(
                    "required unsigned dependency {} missing at {}",
                    dep.ref_id, dep.path
                ),
            );
        }
    }
}

pub fn verification_result_to_json(result: &AuditExportVerificationResult) -> Value {
    serde_json::to_value(result).expect("verification result json")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::audit_export_bundle::{
        build_test_zip, manifest_from_parts, BundleFileEntry, EvidenceRef, FindingRef,
        UnsignedDependency, DEFAULT_AUDIT_EXPORT_PATH, DEFAULT_MANIFEST_PATH,
    };
    use crate::audit_export_signing::{sign_audit_export_ed25519, signing_key_from_seed};
    use crate::bundle::portable_evidence_digest_v1;
    use crate::policy_signing::PolicyTrustStore;
    use crate::replay_validation::EXPORT_SCHEMA_V1;
    use crate::schema::EvidenceEvent;
    use serde_json::json;
    use std::collections::BTreeMap;

    const TEST_SEED: [u8; 32] = [0x22; 32];

    fn trust_store() -> PolicyTrustStore {
        let vk = crate::audit_export_signing::verifying_key_from_seed(&TEST_SEED);
        let mut map = std::collections::BTreeMap::new();
        map.insert("govai-export-signer".to_string(), vec![vk]);
        PolicyTrustStore {
            ed25519_pubkeys: map,
        }
    }

    fn minimal_export(run_id: &str) -> serde_json::Value {
        let events = json!([{
            "event_id": format!("{run_id}-e1"),
            "event_type": "ai_discovery_reported",
            "ts_utc": "2026-01-01T00:00:01Z",
            "actor": "test",
            "system": "test",
            "run_id": run_id,
            "payload": {"openai": false, "transformers": false, "model_artifacts": false}
        }]);
        let events_vec: Vec<EvidenceEvent> =
            serde_json::from_value(events.clone()).expect("events");
        let events_sha = portable_evidence_digest_v1(run_id, &events_vec);
        json!({
            "ok": true,
            "schema_version": EXPORT_SCHEMA_V1,
            "policy_version": "test-policy",
            "environment": "dev",
            "run": {"run_id": run_id},
            "evidence_hashes": {
                "bundle_sha256": "a".repeat(64),
                "events_content_sha256": events_sha,
                "chain_head_record_sha256": "b".repeat(64),
                "log_chain": []
            },
            "decision": {"verdict": "BLOCKED", "evaluation_passed": false},
            "evidence_events": events,
            "evidence_requirements": {
                "required_evidence": [],
                "provided_evidence": [],
                "missing_evidence": []
            }
        })
    }

    fn signed_export(run_id: &str) -> Vec<u8> {
        let mut export = minimal_export(run_id);
        sign_audit_export_ed25519(
            &mut export,
            "govai-export-signer",
            "test",
            &signing_key_from_seed(&TEST_SEED),
            "2026-01-01T00:00:00Z",
            None,
        )
        .expect("sign");
        serde_json::to_vec_pretty(&export).expect("json")
    }

    fn build_valid_bundle(run_id: &str, extra: BundleExtra) -> Vec<u8> {
        let export_bytes = signed_export(run_id);
        let export_hash = sha256_content_hex(&export_bytes);
        let mut files = vec![BundleFileEntry {
            path: DEFAULT_AUDIT_EXPORT_PATH.to_string(),
            sha256: export_hash,
            required: true,
            unsigned: false,
        }];
        let mut entries: BTreeMap<String, Vec<u8>> = BTreeMap::new();
        entries.insert(DEFAULT_AUDIT_EXPORT_PATH.to_string(), export_bytes);

        let mut evidence_refs = Vec::new();
        let mut finding_refs = Vec::new();
        let mut unsigned_dependencies = Vec::new();

        if let Some(att) = extra.attachment {
            let hash = sha256_content_hex(&att.content);
            files.push(BundleFileEntry {
                path: att.path.clone(),
                sha256: hash,
                required: true,
                unsigned: att.unsigned,
            });
            entries.insert(att.path.clone(), att.content);
            evidence_refs.push(EvidenceRef {
                ref_id: att.ref_id.clone(),
                path: att.path.clone(),
            });
        }

        if let Some(f) = extra.finding {
            let hash = sha256_content_hex(&f.content);
            files.push(BundleFileEntry {
                path: f.path.clone(),
                sha256: hash,
                required: true,
                unsigned: false,
            });
            entries.insert(f.path.clone(), f.content);
            finding_refs.push(FindingRef {
                finding_id: f.finding_id.clone(),
                path: f.path.clone(),
            });
        }

        if let Some(dep) = extra.unsigned_dep {
            unsigned_dependencies.push(dep);
        }

        let manifest = manifest_from_parts(
            run_id,
            DEFAULT_AUDIT_EXPORT_PATH,
            files,
            evidence_refs,
            finding_refs,
            unsigned_dependencies,
        );
        let manifest_bytes = crate::audit_export_bundle::build_manifest_json(&manifest).expect("manifest");
        entries.insert(DEFAULT_MANIFEST_PATH.to_string(), manifest_bytes);
        build_test_zip(entries)
    }

    struct BundleExtra {
        attachment: Option<AttachmentSpec>,
        finding: Option<FindingSpec>,
        unsigned_dep: Option<UnsignedDependency>,
    }

    struct AttachmentSpec {
        path: String,
        content: Vec<u8>,
        ref_id: String,
        unsigned: bool,
    }

    struct FindingSpec {
        path: String,
        content: Vec<u8>,
        finding_id: String,
    }

    fn verify(zip: &[u8]) -> AuditExportVerificationResult {
        verify_audit_export_bundle_bytes(
            zip,
            VerifyAuditExportBundleOptions {
                trust: &trust_store(),
                expected_issuer_id: None,
                policy_cfg: None,
            },
        )
    }

    #[test]
    fn valid_bundle_passes() {
        let zip = build_valid_bundle(
            "run-valid",
            BundleExtra {
                attachment: Some(AttachmentSpec {
                    path: "evidence/discovery.json".to_string(),
                    content: br#"{"ok":true}"#.to_vec(),
                    ref_id: "evidence:discovery".to_string(),
                    unsigned: false,
                }),
                finding: Some(FindingSpec {
                    path: "findings/f1.json".to_string(),
                    content: br#"{"finding":"none"}"#.to_vec(),
                    finding_id: "finding:1".to_string(),
                }),
                unsigned_dep: None,
            },
        );
        let result = verify(&zip);
        assert_eq!(result.overall_status, "success");
        assert!(result.signature_verified);
        assert!(result.canonical_bundle_digest_verified);
        assert!(result.replay_validation_passed);
    }

    #[test]
    fn valid_signature_modified_attachment_fails_hash() {
        let mut zip = build_valid_bundle(
            "run-tamper",
            BundleExtra {
                attachment: Some(AttachmentSpec {
                    path: "evidence/discovery.json".to_string(),
                    content: br#"{"ok":true}"#.to_vec(),
                    ref_id: "evidence:discovery".to_string(),
                    unsigned: false,
                }),
                finding: None,
                unsigned_dep: None,
            },
        );
        let mut entries = read_zip_entries(&zip).expect("read");
        entries.insert(
            "evidence/discovery.json".to_string(),
            br#"{"ok":false}"#.to_vec(),
        );
        zip = build_test_zip(entries);
        let result = verify(&zip);
        assert!(!result.all_manifest_hashes_match);
        assert!(result.signature_verified);
        assert_ne!(result.overall_status, "success");
        assert_eq!(result.overall_status, "hash_mismatch");
    }

    #[test]
    fn valid_signature_missing_manifest_file_fails() {
        let zip = build_valid_bundle(
            "run-missing-file",
            BundleExtra {
                attachment: Some(AttachmentSpec {
                    path: "evidence/discovery.json".to_string(),
                    content: br#"{"ok":true}"#.to_vec(),
                    ref_id: "evidence:discovery".to_string(),
                    unsigned: false,
                }),
                finding: None,
                unsigned_dep: None,
            },
        );
        let mut entries = read_zip_entries(&zip).expect("read");
        entries.remove("evidence/discovery.json");
        let zip = build_test_zip(entries);
        let result = verify(&zip);
        assert!(!result.manifest_complete);
        assert_eq!(result.overall_status, "missing_evidence");
    }

    #[test]
    fn valid_signature_missing_evidence_reference_fails() {
        let zip = build_valid_bundle(
            "run-missing-ref",
            BundleExtra {
                attachment: None,
                finding: None,
                unsigned_dep: None,
            },
        );
        let mut entries = read_zip_entries(&zip).expect("read");
        let manifest: AuditExportBundleManifest =
            parse_manifest_bytes(entries.get(DEFAULT_MANIFEST_PATH).unwrap()).expect("manifest");
        let mut broken = manifest.clone();
        broken.evidence_refs = vec![EvidenceRef {
            ref_id: "evidence:ghost".to_string(),
            path: "evidence/missing.json".to_string(),
        }];
        broken.canonical_bundle_digest_sha256 =
            crate::audit_export_bundle::compute_canonical_bundle_digest(&broken);
        entries.insert(
            DEFAULT_MANIFEST_PATH.to_string(),
            crate::audit_export_bundle::build_manifest_json(&broken).expect("manifest"),
        );
        let zip = build_test_zip(entries);
        let result = verify(&zip);
        assert!(!result.all_evidence_references_resolve);
        assert_eq!(result.overall_status, "missing_evidence");
    }

    #[test]
    fn unsupported_schema_version_fails() {
        let zip = build_valid_bundle(
            "run-schema",
            BundleExtra {
                attachment: None,
                finding: None,
                unsigned_dep: None,
            },
        );
        let mut entries = read_zip_entries(&zip).expect("read");
        let mut manifest: AuditExportBundleManifest =
            parse_manifest_bytes(entries.get(DEFAULT_MANIFEST_PATH).unwrap()).expect("manifest");
        manifest.schema_version = "aigov.audit_export_bundle.v99".to_string();
        manifest.canonical_bundle_digest_sha256 =
            crate::audit_export_bundle::compute_canonical_bundle_digest(&manifest);
        entries.insert(
            DEFAULT_MANIFEST_PATH.to_string(),
            crate::audit_export_bundle::build_manifest_json(&manifest).expect("manifest"),
        );
        let zip = build_test_zip(entries);
        let result = verify(&zip);
        assert!(!result.schema_version_supported);
        assert_eq!(result.overall_status, "unsupported_schema_version");
    }

    fn apply_signed_export(
        entries: &mut BTreeMap<String, Vec<u8>>,
        manifest: &mut AuditExportBundleManifest,
        mut export: serde_json::Value,
    ) {
        sign_audit_export_ed25519(
            &mut export,
            "govai-export-signer",
            "test",
            &signing_key_from_seed(&TEST_SEED),
            "2026-01-01T00:00:00Z",
            None,
        )
        .expect("sign");
        let export_bytes = serde_json::to_vec_pretty(&export).expect("json");
        let export_hash = sha256_content_hex(&export_bytes);
        for file in &mut manifest.files {
            if file.path == DEFAULT_AUDIT_EXPORT_PATH {
                file.sha256 = export_hash.clone();
            }
        }
        manifest.canonical_bundle_digest_sha256 =
            crate::audit_export_bundle::compute_canonical_bundle_digest(manifest);
        entries.insert(DEFAULT_AUDIT_EXPORT_PATH.to_string(), export_bytes);
        entries.insert(
            DEFAULT_MANIFEST_PATH.to_string(),
            crate::audit_export_bundle::build_manifest_json(manifest).expect("manifest"),
        );
    }

    #[test]
    fn broken_hash_chain_fails() {
        let zip = build_valid_bundle(
            "run-chain",
            BundleExtra {
                attachment: None,
                finding: None,
                unsigned_dep: None,
            },
        );
        let mut entries = read_zip_entries(&zip).expect("read");
        let mut manifest: AuditExportBundleManifest =
            parse_manifest_bytes(entries.get(DEFAULT_MANIFEST_PATH).unwrap()).expect("manifest");
        let mut export: serde_json::Value =
            serde_json::from_slice(entries.get(DEFAULT_AUDIT_EXPORT_PATH).unwrap()).expect("export");
        export["evidence_hashes"]["log_chain"] = json!([
            {
                "event_id": "run-chain-e1",
                "ts_utc": "2026-01-01T00:00:01Z",
                "event_type": "ai_discovery_reported",
                "prev_hash": "genesis",
                "record_hash": "a".repeat(64),
            },
            {
                "event_id": "run-chain-e2",
                "ts_utc": "2026-01-01T00:00:02Z",
                "event_type": "ai_discovery_reported",
                "prev_hash": "broken-link",
                "record_hash": "b".repeat(64),
            }
        ]);
        apply_signed_export(&mut entries, &mut manifest, export);
        let zip = build_test_zip(entries);
        let result = verify(&zip);
        assert!(!result.replay_validation_passed);
        assert_eq!(result.overall_status, "replay_validation_failure");
    }

    #[test]
    fn reordered_manifest_keys_still_verifies() {
        let zip = build_valid_bundle(
            "run-order",
            BundleExtra {
                attachment: None,
                finding: None,
                unsigned_dep: None,
            },
        );
        let mut entries = read_zip_entries(&zip).expect("read");
        let manifest: AuditExportBundleManifest =
            parse_manifest_bytes(entries.get(DEFAULT_MANIFEST_PATH).unwrap()).expect("manifest");
        let reordered = json!({
            "unsigned_dependencies": manifest.unsigned_dependencies,
            "finding_refs": manifest.finding_refs,
            "evidence_refs": manifest.evidence_refs,
            "run_id": manifest.run_id,
            "audit_export_path": manifest.audit_export_path,
            "files": manifest.files,
            "schema_version": manifest.schema_version,
            "canonical_bundle_digest_sha256": manifest.canonical_bundle_digest_sha256,
        });
        entries.insert(
            DEFAULT_MANIFEST_PATH.to_string(),
            serde_json::to_vec_pretty(&reordered).expect("json"),
        );
        let zip = build_test_zip(entries);
        let result = verify(&zip);
        assert!(result.canonical_bundle_digest_verified);
        assert_eq!(result.overall_status, "success");
    }

    #[test]
    fn changed_canonical_content_fails_digest() {
        let zip = build_valid_bundle(
            "run-content",
            BundleExtra {
                attachment: None,
                finding: None,
                unsigned_dep: None,
            },
        );
        let mut entries = read_zip_entries(&zip).expect("read");
        let mut manifest: AuditExportBundleManifest =
            parse_manifest_bytes(entries.get(DEFAULT_MANIFEST_PATH).unwrap()).expect("manifest");
        manifest.run_id = "run-tampered".to_string();
        entries.insert(
            DEFAULT_MANIFEST_PATH.to_string(),
            crate::audit_export_bundle::build_manifest_json(&manifest).expect("manifest"),
        );
        let zip = build_test_zip(entries);
        let result = verify(&zip);
        assert!(!result.canonical_bundle_digest_verified);
        assert_eq!(result.overall_status, "bundle_tampered");
    }

    #[test]
    fn extra_unsigned_dependency_missing_fails() {
        let zip = build_valid_bundle(
            "run-unsigned",
            BundleExtra {
                attachment: None,
                finding: None,
                unsigned_dep: Some(UnsignedDependency {
                    ref_id: "report:summary".to_string(),
                    path: "attachments/report.md".to_string(),
                    required_for_explanation: true,
                }),
            },
        );
        let result = verify(&zip);
        assert!(result.unsigned_dependency_detected);
        assert_eq!(result.overall_status, "missing_evidence");
    }

    #[test]
    fn replay_validation_failure_while_signature_still_valid() {
        let zip = build_valid_bundle(
            "run-replay-fail",
            BundleExtra {
                attachment: None,
                finding: None,
                unsigned_dep: None,
            },
        );
        let mut entries = read_zip_entries(&zip).expect("read");
        let mut manifest: AuditExportBundleManifest =
            parse_manifest_bytes(entries.get(DEFAULT_MANIFEST_PATH).unwrap()).expect("manifest");
        let mut export: serde_json::Value =
            serde_json::from_slice(entries.get(DEFAULT_AUDIT_EXPORT_PATH).unwrap()).expect("export");
        export["evidence_hashes"]["log_chain"] = json!([
            {
                "event_id": "run-replay-fail-e1",
                "ts_utc": "2026-01-01T00:00:01Z",
                "event_type": "ai_discovery_reported",
                "prev_hash": "genesis",
                "record_hash": "a".repeat(64),
            },
            {
                "event_id": "run-replay-fail-e2",
                "ts_utc": "2026-01-01T00:00:02Z",
                "event_type": "ai_discovery_reported",
                "prev_hash": "broken-link",
                "record_hash": "b".repeat(64),
            }
        ]);
        apply_signed_export(&mut entries, &mut manifest, export);
        let zip = build_test_zip(entries);
        let result = verify(&zip);
        assert!(result.signature_verified);
        assert!(!result.replay_validation_passed);
        assert_eq!(result.overall_status, "replay_validation_failure");
    }
}
