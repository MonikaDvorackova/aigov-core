//! Ed25519 signing and verification for ``aigov.audit_export.v1`` documents.

use crate::bundle::portable_evidence_digest_v1;
use crate::canonical_json::{canonical_json_bytes, sha256_hex_bytes, sort_json_value};
use crate::policy_signing::PolicyTrustStore;
use crate::replay_validation::{export_run_id, EXPORT_SCHEMA_V1};
use crate::schema::EvidenceEvent;
use base64::Engine;
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

pub const SIGNATURE_KIND_ED25519: &str = "ed25519";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AuditExportSigningPayload {
    pub schema_version: String,
    pub run_id: String,
    pub policy_version: String,
    pub environment: String,
    pub bundle_sha256: String,
    pub events_content_sha256: String,
    pub chain_head_record_sha256: String,
    pub decision_verdict: String,
}

pub fn canonical_audit_export_signing_payload(export: &Value) -> AuditExportSigningPayload {
    let mut doc = export.clone();
    if let Some(obj) = doc.as_object_mut() {
        obj.remove("signatures");
    }
    let eh = doc
        .get("evidence_hashes")
        .and_then(|v| v.as_object())
        .cloned()
        .unwrap_or_default();
    let decision = doc
        .get("decision")
        .and_then(|v| v.as_object())
        .cloned()
        .unwrap_or_default();
    let chain_head = eh
        .get("chain_head_record_sha256")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    AuditExportSigningPayload {
        schema_version: doc
            .get("schema_version")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_string(),
        run_id: export_run_id(&doc).unwrap_or_default(),
        policy_version: doc
            .get("policy_version")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_string(),
        environment: doc
            .get("environment")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_string(),
        bundle_sha256: eh
            .get("bundle_sha256")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_ascii_lowercase(),
        events_content_sha256: eh
            .get("events_content_sha256")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_ascii_lowercase(),
        chain_head_record_sha256: chain_head.trim().to_ascii_lowercase(),
        decision_verdict: decision
            .get("verdict")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_string(),
    }
}

pub fn audit_export_payload_digest_sha256_hex(export: &Value) -> String {
    let payload = canonical_audit_export_signing_payload(export);
    sha256_hex_bytes(&canonical_json_bytes(&payload))
}

fn require_sha256_hex(label: &str, value: &str) -> Result<String, String> {
    let v = value.trim().to_ascii_lowercase();
    if v.len() != 64 || !v.chars().all(|c| c.is_ascii_hexdigit()) {
        return Err(format!("{label} must be 64 lowercase hex characters"));
    }
    Ok(v)
}

pub fn validate_export_schema_version(export: &Value) -> Result<(), String> {
    let schema = export
        .get("schema_version")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .trim();
    if schema != EXPORT_SCHEMA_V1 {
        return Err(format!(
            "unsupported export schema {schema:?} (expected {EXPORT_SCHEMA_V1})"
        ));
    }
    Ok(())
}

pub fn validate_export_run_id_consistency(export: &Value) -> Result<String, String> {
    let run_id = export_run_id(export).ok_or_else(|| "run.run_id is missing or empty".to_string())?;
    let events = export
        .get("evidence_events")
        .and_then(|v| v.as_array())
        .ok_or_else(|| "evidence_events must be an array".to_string())?;
    for (i, ev) in events.iter().enumerate() {
        let ev_run = ev
            .get("run_id")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim();
        if ev_run != run_id {
            return Err(format!(
                "evidence_events[{i}].run_id {ev_run:?} inconsistent with run.run_id {run_id:?}"
            ));
        }
    }
    Ok(run_id)
}

pub fn validate_events_content_sha256(export: &Value, run_id: &str) -> Result<(), String> {
    let eh = export
        .get("evidence_hashes")
        .and_then(|v| v.as_object())
        .ok_or_else(|| "evidence_hashes must be an object".to_string())?;
    let declared = require_sha256_hex(
        "evidence_hashes.events_content_sha256",
        eh.get("events_content_sha256")
            .and_then(|v| v.as_str())
            .unwrap_or(""),
    )?;
    let events = export
        .get("evidence_events")
        .and_then(|v| v.as_array())
        .ok_or_else(|| "evidence_events must be an array".to_string())?;
    let mut parsed: Vec<EvidenceEvent> = Vec::with_capacity(events.len());
    for (i, item) in events.iter().enumerate() {
        let ev: EvidenceEvent = serde_json::from_value(item.clone())
            .map_err(|e| format!("evidence_events[{i}] invalid: {e}"))?;
        parsed.push(ev);
    }
    let recomputed = portable_evidence_digest_v1(run_id, &parsed);
    if recomputed != declared {
        return Err(
            "events_content_sha256 mismatch: export evidence does not match recomputed digest"
                .to_string(),
        );
    }
    Ok(())
}

pub fn validate_bundle_sha256_field(export: &Value) -> Result<String, String> {
    let eh = export
        .get("evidence_hashes")
        .and_then(|v| v.as_object())
        .ok_or_else(|| "evidence_hashes must be an object".to_string())?;
    require_sha256_hex(
        "evidence_hashes.bundle_sha256",
        eh.get("bundle_sha256")
            .and_then(|v| v.as_str())
            .unwrap_or(""),
    )
}

pub fn validate_signed_audit_export_integrity(export: &Value) -> Result<AuditExportSigningPayload, String> {
    validate_export_schema_version(export)?;
    let run_id = validate_export_run_id_consistency(export)?;
    validate_events_content_sha256(export, &run_id)?;
    validate_bundle_sha256_field(export)?;
    let payload = canonical_audit_export_signing_payload(export);
    if payload.run_id != run_id {
        return Err("canonical signing payload run_id mismatch".to_string());
    }
    Ok(payload)
}

pub fn verify_audit_export_ed25519_signature(
    export: &Value,
    trust: &PolicyTrustStore,
    expected_issuer_id: Option<&str>,
) -> Result<String, String> {
    validate_signed_audit_export_integrity(export)?;
    let digest = audit_export_payload_digest_sha256_hex(export);

    let sigs = export
        .get("signatures")
        .and_then(|v| v.as_array())
        .filter(|a| !a.is_empty())
        .ok_or_else(|| "export is unsigned (signatures missing or empty)".to_string())?;

    let mut last_err = "no valid export signature found".to_string();
    for s in sigs {
        let Some(sig_obj) = s.as_object() else {
            last_err = "signature record must be an object".to_string();
            continue;
        };
        if sig_obj
            .get("kind")
            .and_then(|v| v.as_str())
            != Some(SIGNATURE_KIND_ED25519)
        {
            last_err = "unsupported signature kind".to_string();
            continue;
        }
        if sig_obj
            .get("payload_digest_sha256")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_ascii_lowercase()
            != digest
        {
            last_err = "payload digest mismatch".to_string();
            continue;
        }
        let issuer_id = sig_obj
            .get("issuer_id")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim();
        if issuer_id.is_empty() {
            last_err = "signature issuer_id missing".to_string();
            continue;
        }
        if let Some(expected) = expected_issuer_id {
            if expected.trim() != issuer_id {
                last_err = format!("signature issuer_id {issuer_id} does not match expected {expected}");
                continue;
            }
        }
        let sig = sig_obj.get("signature").and_then(|v| v.as_object());
        let Some(sig) = sig else {
            last_err = "signature object missing".to_string();
            continue;
        };
        if sig.get("encoding").and_then(|v| v.as_str()) != Some("base64") {
            last_err = "unsupported signature encoding".to_string();
            continue;
        }
        let sig_b64 = sig.get("value").and_then(|v| v.as_str()).unwrap_or("").trim();
        if sig_b64.is_empty() {
            last_err = "signature value empty".to_string();
            continue;
        }
        let sig_bytes = base64::engine::general_purpose::STANDARD
            .decode(sig_b64)
            .map_err(|e| format!("invalid signature base64: {e}"))?;
        let signature = Signature::from_slice(sig_bytes.as_slice())
            .map_err(|e| format!("invalid ed25519 signature bytes: {e}"))?;

        let keys = match trust.ed25519_pubkeys.get(issuer_id) {
            Some(k) => k,
            None => {
                last_err = format!("no trusted keys for issuer_id={issuer_id}");
                continue;
            }
        };
        for vk in keys {
            if vk.verify(digest.as_bytes(), &signature).is_ok() {
                return Ok(issuer_id.to_string());
            }
            last_err = "ed25519 verify failed".to_string();
        }
    }
    Err(last_err)
}

pub fn sign_audit_export_ed25519(
    export: &mut Value,
    issuer_id: &str,
    signer: &str,
    signing_key: &SigningKey,
    created_at_utc: &str,
    expires_at_utc: Option<&str>,
) -> Result<(), String> {
    validate_signed_audit_export_integrity(export)?;
    let digest = audit_export_payload_digest_sha256_hex(export);
    let payload = canonical_audit_export_signing_payload(export);
    let sig_bytes = signing_key.sign(digest.as_bytes());
    let sig_b64 = base64::engine::general_purpose::STANDARD.encode(sig_bytes.to_bytes());

    let sig_record = json!({
        "kind": SIGNATURE_KIND_ED25519,
        "issuer_id": issuer_id.trim(),
        "signer": signer.trim(),
        "created_at_utc": created_at_utc,
        "expires_at_utc": expires_at_utc,
        "payload_digest_sha256": digest,
        "canonical_payload": sort_json_value(serde_json::to_value(&payload).expect("payload json")),
        "signature": {"encoding": "base64", "value": sig_b64},
    });

    match export.get_mut("signatures") {
        None => {
            export
                .as_object_mut()
                .expect("export object")
                .insert("signatures".to_string(), json!([sig_record]));
        }
        Some(v) => {
            let arr = v
                .as_array_mut()
                .ok_or_else(|| "export.signatures must be an array when present".to_string())?;
            arr.push(sig_record);
        }
    }
    Ok(())
}

pub fn signing_key_from_seed(seed: &[u8; 32]) -> SigningKey {
    SigningKey::from_bytes(seed)
}

pub fn verifying_key_from_seed(seed: &[u8; 32]) -> VerifyingKey {
    SigningKey::from_bytes(seed).verifying_key()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::policy_signing::PolicyTrustStore;
    use std::collections::BTreeMap;

    fn minimal_export(run_id: &str) -> Value {
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
            "decision": {"verdict": "BLOCKED"},
            "evidence_events": events
        })
    }

    fn trust_for_seed(seed: [u8; 32]) -> PolicyTrustStore {
        let vk = verifying_key_from_seed(&seed);
        let pk_b64 = base64::engine::general_purpose::STANDARD.encode(vk.as_bytes());
        let mut map = BTreeMap::new();
        map.insert("govai-export-signer".to_string(), vec![vk]);
        let _ = pk_b64;
        PolicyTrustStore {
            ed25519_pubkeys: map,
        }
    }

    #[test]
    fn sign_and_verify_roundtrip() {
        let seed = [0x22; 32];
        let sk = signing_key_from_seed(&seed);
        let trust = trust_for_seed(seed);
        let mut export = minimal_export("run-sign-test");
        sign_audit_export_ed25519(
            &mut export,
            "govai-export-signer",
            "test",
            &sk,
            "2026-01-01T00:00:00Z",
            None,
        )
        .expect("sign");
        let issuer = verify_audit_export_ed25519_signature(&export, &trust, None).expect("verify");
        assert_eq!(issuer, "govai-export-signer");
    }
}
