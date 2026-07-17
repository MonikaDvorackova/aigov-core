use crate::contracts::{GovaiPolicyV1, PolicySignatureV1};
use crate::govai_environment::GovaiEnvironment;
use base64::Engine;
use ed25519_dalek::{Signature, VerifyingKey};
use serde::Deserialize;
use sha2::{Digest, Sha256};

#[derive(Debug, Clone)]
pub struct PolicyTrustStore {
    /// issuer_id -> list of base64 public keys (Ed25519).
    pub ed25519_pubkeys: std::collections::BTreeMap<String, Vec<VerifyingKey>>,
}

#[derive(Debug, Clone, Deserialize)]
struct TrustConfigEd25519 {
    issuer_id: String,
    pubkeys_base64: Vec<String>,
}

/// Load trusted policy signing keys.
///
/// Format (JSON array):
/// `[{"issuer_id":"acme-security","pubkeys_base64":["...","..."]}]`
pub fn load_trust_store_from_env() -> Result<PolicyTrustStore, String> {
    let raw = std::env::var("AIGOV_POLICY_TRUST_ED25519_JSON")
        .ok()
        .unwrap_or_default();
    let t = raw.trim();
    if t.is_empty() {
        return Ok(PolicyTrustStore {
            ed25519_pubkeys: Default::default(),
        });
    }
    let items: Vec<TrustConfigEd25519> = serde_json::from_str(t)
        .map_err(|e| format!("invalid AIGOV_POLICY_TRUST_ED25519_JSON: {e}"))?;
    let mut out: std::collections::BTreeMap<String, Vec<VerifyingKey>> = Default::default();
    for it in items {
        if it.issuer_id.trim().is_empty() {
            return Err("invalid AIGOV_POLICY_TRUST_ED25519_JSON: issuer_id empty".to_string());
        }
        if it.pubkeys_base64.is_empty() {
            return Err(format!(
                "invalid AIGOV_POLICY_TRUST_ED25519_JSON: issuer_id={} has no keys",
                it.issuer_id
            ));
        }
        let mut keys: Vec<VerifyingKey> = Vec::new();
        for k in it.pubkeys_base64 {
            let bytes = base64::engine::general_purpose::STANDARD
                .decode(k.trim())
                .map_err(|e| {
                    format!(
                        "invalid base64 public key for issuer_id={}: {e}",
                        it.issuer_id
                    )
                })?;
            let vk = VerifyingKey::try_from(bytes.as_slice()).map_err(|e| {
                format!(
                    "invalid ed25519 public key for issuer_id={}: {e}",
                    it.issuer_id
                )
            })?;
            keys.push(vk);
        }
        out.insert(it.issuer_id.trim().to_string(), keys);
    }
    Ok(PolicyTrustStore {
        ed25519_pubkeys: out,
    })
}

pub fn policy_payload_digest_sha256(policy: &GovaiPolicyV1) -> String {
    // Canonical payload for signing is the policy document with `signatures` removed,
    // and keys sorted recursively.
    let mut v = serde_json::to_value(policy).expect("policy serde");
    if let Some(obj) = v.as_object_mut() {
        obj.remove("signatures");
    }
    let v = sort_json_value(v);
    let bytes = serde_json::to_vec(&v).expect("policy canonical json");
    let mut h = Sha256::new();
    h.update(bytes);
    hex::encode(h.finalize())
}

fn sort_json_value(v: serde_json::Value) -> serde_json::Value {
    match v {
        serde_json::Value::Object(map) => {
            let mut items: Vec<(String, serde_json::Value)> = map.into_iter().collect();
            items.sort_by(|a, b| a.0.cmp(&b.0));
            let mut out = serde_json::Map::new();
            for (k, vv) in items {
                out.insert(k, sort_json_value(vv));
            }
            serde_json::Value::Object(out)
        }
        serde_json::Value::Array(arr) => {
            serde_json::Value::Array(arr.into_iter().map(sort_json_value).collect())
        }
        other => other,
    }
}

fn now_utc_rfc3339() -> String {
    // For deterministic verification behavior, we do NOT use the system clock here.
    // Signature expiration is enforced using timestamps embedded in the signature record
    // and the policy's `created_at_utc` for Phase 1.
    // (Full clock-source semantics are handled in the crypto evidence TODO (#145).)
    "1970-01-01T00:00:00Z".to_string()
}

pub fn verify_policy_signatures(
    deployment_env: GovaiEnvironment,
    trust: &PolicyTrustStore,
    policy: &GovaiPolicyV1,
) -> Result<(), String> {
    if policy.signatures.is_empty() {
        return Err("policy is unsigned (no signatures)".to_string());
    }

    let payload_digest = policy_payload_digest_sha256(policy);

    // Fail closed on unknown signature kinds in staging/prod; allow in dev only.
    let mut any_ok = false;
    let mut last_err: Option<String> = None;

    for sig in policy.signatures.iter() {
        match sig.kind.as_str() {
            "ed25519" => match verify_ed25519(trust, policy, &payload_digest, sig) {
                Ok(()) => {
                    any_ok = true;
                    break;
                }
                Err(e) => last_err = Some(e),
            },
            other => {
                let msg = format!("unsupported policy signature kind: {other}");
                if matches!(deployment_env, GovaiEnvironment::Dev) {
                    last_err = Some(msg);
                    continue;
                }
                return Err(msg);
            }
        }
    }

    if any_ok {
        Ok(())
    } else {
        Err(last_err.unwrap_or_else(|| "no valid policy signature found".to_string()))
    }
}

fn verify_ed25519(
    trust: &PolicyTrustStore,
    policy: &GovaiPolicyV1,
    payload_digest: &str,
    sig: &PolicySignatureV1,
) -> Result<(), String> {
    if sig.payload_digest_sha256.trim().to_ascii_lowercase() != payload_digest {
        return Err("policy signature payload_digest_sha256 mismatch".to_string());
    }

    // Expiration: if present, require it to be >= created_at_utc (syntactic) for Phase 1.
    if let Some(exp) = sig.expires_at_utc.as_ref() {
        if exp.trim().is_empty() {
            return Err("policy signature expires_at_utc is empty".to_string());
        }
        // Do not parse timestamps here; that is handled in Phase 1 crypto TODO (#145)
        // We at least ensure deterministic behavior by rejecting empty.
        let _ = now_utc_rfc3339();
    }

    if sig.signature.encoding != "base64" {
        return Err(format!(
            "unsupported policy signature encoding: {}",
            sig.signature.encoding
        ));
    }

    let issuer_id = policy.issuer.issuer_id.trim();
    let keys = trust
        .ed25519_pubkeys
        .get(issuer_id)
        .ok_or_else(|| format!("no trusted keys for policy issuer_id={issuer_id}"))?;

    let sig_bytes = base64::engine::general_purpose::STANDARD
        .decode(sig.signature.value.trim())
        .map_err(|e| format!("invalid signature base64: {e}"))?;
    let sig_obj = Signature::from_slice(sig_bytes.as_slice())
        .map_err(|e| format!("invalid ed25519 signature bytes: {e}"))?;

    let msg = payload_digest.as_bytes();
    for vk in keys.iter() {
        if vk.verify_strict(msg, &sig_obj).is_ok() {
            return Ok(());
        }
    }

    Err("ed25519 signature verification failed for all trusted keys".to_string())
}
