use serde::{Deserialize, Serialize};

/// Contract: `govai.policy.v1` (see `contracts/govai.policy.v1.schema.json`).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct GovaiPolicyV1 {
    pub schema: String,
    pub policy_id: String,
    pub version: String,
    pub created_at_utc: String,
    pub issuer: PolicyIssuerV1,
    pub selectors: PolicySelectorsV1,
    #[serde(default)]
    pub inherits: Vec<PolicyRefV1>,
    pub ingest_rules: IngestRulesV1,
    pub verdict_rules: VerdictRulesV1,
    pub signatures: Vec<PolicySignatureV1>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct PolicyIssuerV1 {
    pub issuer_id: String,
    pub display_name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub contact: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct PolicySelectorsV1 {
    pub tenants: Vec<String>,
    pub environments: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct PolicyRefV1 {
    pub policy_id: String,
    pub version: String,
    pub digest_sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct IngestRulesV1 {
    pub unknown_event_types: UnknownEventTypesV1,
    pub event_types: std::collections::BTreeMap<String, EventTypeRulesV1>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct UnknownEventTypesV1 {
    pub behavior: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct EventTypeRulesV1 {
    #[serde(default)]
    pub schema: serde_json::Value,
    #[serde(default)]
    pub gates: Vec<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct VerdictRulesV1 {
    pub required_evidence_codes: Vec<String>,
    pub invalid_conditions: Vec<InvalidConditionV1>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct InvalidConditionV1 {
    pub code: String,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct PolicySignatureV1 {
    pub kind: String,
    pub signer: String,
    pub created_at_utc: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub expires_at_utc: Option<String>,
    pub payload_digest_sha256: String,
    pub signature: SignatureValueV1,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub sigstore: Option<SigstoreHintsV1>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct SignatureValueV1 {
    pub encoding: String,
    pub value: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct SigstoreHintsV1 {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rekor_log_index: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rekor_uuid: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub fulcio_issuer: Option<String>,
}

/// Contract: `govai.immutable_anchor.v1` (see `contracts/govai.immutable_anchor.v1.schema.json`).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct GovaiImmutableAnchorV1 {
    pub schema: String,
    pub created_at_utc: String,
    pub ok: bool,
    pub tenant_id: String,
    pub environment: String,
    pub ledger: AnchorLedgerV1,
    pub checkpoint: AnchorCheckpointV1,
    pub evidence_hashes: AnchorEvidenceHashesV1,
    pub policy: AnchorPolicyRefV1,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub sigstore: Option<AnchorSigstoreV1>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct AnchorLedgerV1 {
    pub path_label: String,
    pub chain_head_record_sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct AnchorCheckpointV1 {
    pub run_id: String,
    pub last_event_id: String,
    pub events_content_sha256: String,
    pub ts_utc: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct AnchorEvidenceHashesV1 {
    pub events_content_sha256: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub bundle_sha256: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct AnchorPolicyRefV1 {
    pub policy_id: String,
    pub version: String,
    pub digest_sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct AnchorSigstoreV1 {
    #[serde(default)]
    pub rekor_entries: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn contracts_deserialize_strictly_and_roundtrip_minimal_policy() {
        let raw = serde_json::json!({
          "schema": "govai.policy.v1",
          "policy_id": "p",
          "version": "1",
          "created_at_utc": "2026-01-01T00:00:00Z",
          "issuer": { "issuer_id": "i", "display_name": "Issuer" },
          "selectors": { "tenants": ["t1"], "environments": ["dev"] },
          "inherits": [],
          "ingest_rules": {
            "unknown_event_types": { "behavior": "reject" },
            "event_types": {}
          },
          "verdict_rules": {
            "required_evidence_codes": [],
            "invalid_conditions": []
          },
          "signatures": [{
            "kind": "ed25519",
            "signer": "s",
            "created_at_utc": "2026-01-01T00:00:00Z",
            "expires_at_utc": null,
            "payload_digest_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "signature": { "encoding": "base64", "value": "c2ln" },
            "sigstore": null
          }]
        });

        let p: GovaiPolicyV1 = serde_json::from_value(raw.clone()).expect("deserialize");
        let v = serde_json::to_value(&p).expect("serialize");
        let p2: GovaiPolicyV1 = serde_json::from_value(v).expect("deserialize 2");
        assert_eq!(p, p2);
        assert_eq!(p.schema, "govai.policy.v1");
    }
}
