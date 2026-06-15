use crate::contracts::GovaiPolicyV1;
use crate::govai_environment::GovaiEnvironment;
use crate::policy::PolicyViolation;
use crate::policy_config::{effective_approver_allowlist, PolicyConfig};
use crate::policy_engine::{
    enforce_ingest, EventTypeRule, FieldType, Gate, PayloadSchema, RuntimePolicy,
    UnknownEventTypeBehavior,
};
use crate::policy_signing;
use crate::schema::EvidenceEvent;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;
use std::sync::Arc;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PolicySourceKind {
    BundleFile,
    BundleDir,
    LegacyConfigFile,
    Defaults,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PolicySource {
    pub kind: PolicySourceKind,
    pub path: Option<String>,
}

#[derive(Debug, Clone)]
pub struct ResolvedPolicy {
    pub runtime: RuntimePolicy,
    pub digest_sha256: String,
    pub source: PolicySource,
}

impl ResolvedPolicy {
    pub fn policy_id(&self) -> &str {
        self.runtime.policy_id.as_str()
    }
    pub fn version(&self) -> &str {
        self.runtime.version.as_str()
    }
}

#[derive(Clone)]
pub struct PolicyStore {
    deployment_env: GovaiEnvironment,
    /// Policies loaded from bundle files in memory.
    policies: Arc<Vec<ResolvedPolicy>>,
    /// Legacy fallback compiled into a runtime policy (always present).
    legacy_fallback: Arc<ResolvedPolicy>,
}

impl PolicyStore {
    pub fn load_for_deployment(
        deployment_env: GovaiEnvironment,
        legacy: crate::policy_config::ResolvedPolicyConfig,
    ) -> Result<Self, String> {
        let dir = std::env::var("AIGOV_POLICY_DIR")
            .ok()
            .filter(|s| !s.trim().is_empty())
            .map(|s| PathBuf::from(s.trim()))
            .unwrap_or_else(|| PathBuf::from("."));

        let bundle_override = std::env::var("AIGOV_POLICY_BUNDLE_FILE")
            .ok()
            .filter(|s| !s.trim().is_empty());

        let mut loaded: Vec<ResolvedPolicy> = Vec::new();

        if let Some(p) = bundle_override {
            let p = PathBuf::from(p.trim());
            // Load + verify bundle signatures (fail-closed in staging/prod).
            let raw = std::fs::read_to_string(&p).map_err(|e| e.to_string())?;
            let doc: GovaiPolicyV1 = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
            if !matches!(deployment_env, GovaiEnvironment::Dev) {
                let trust = policy_signing::load_trust_store_from_env()?;
                if trust.ed25519_pubkeys.is_empty() {
                    return Err("Invalid policy configuration: refusing to start — AIGOV_POLICY_TRUST_ED25519_JSON required for signed policy verification".to_string());
                }
                policy_signing::verify_policy_signatures(deployment_env, &trust, &doc)?;
            }
            let rp =
                load_bundle_doc(&doc).map_err(|e| format!("policy bundle load failed: {e}"))?;
            loaded.push(ResolvedPolicy {
                digest_sha256: rp.digest_sha256(),
                runtime: rp,
                source: PolicySource {
                    kind: PolicySourceKind::BundleFile,
                    path: Some(p.display().to_string()),
                },
            });
        } else {
            // Directory mode: load policy bundles from AIGOV_POLICY_DIR (deterministic ordering by filename).
            // Naming convention: `policy.bundle.<env>.json` or `policy.bundle.json`.
            let mut candidates: Vec<PathBuf> = Vec::new();
            let env_label = deployment_env.as_str();
            candidates.push(dir.join(format!("policy.bundle.{env_label}.json")));
            candidates.push(dir.join("policy.bundle.json"));

            for p in candidates {
                if !p.exists() {
                    continue;
                }
                let raw = std::fs::read_to_string(&p).map_err(|e| e.to_string())?;
                let doc: GovaiPolicyV1 = serde_json::from_str(&raw).map_err(|e| e.to_string())?;
                if !matches!(deployment_env, GovaiEnvironment::Dev) {
                    let trust = policy_signing::load_trust_store_from_env()?;
                    if trust.ed25519_pubkeys.is_empty() {
                        return Err("Invalid policy configuration: refusing to start — AIGOV_POLICY_TRUST_ED25519_JSON required for signed policy verification".to_string());
                    }
                    policy_signing::verify_policy_signatures(deployment_env, &trust, &doc)?;
                }
                let rp = load_bundle_doc(&doc)
                    .map_err(|e| format!("policy bundle load failed {}: {e}", p.display()))?;
                loaded.push(ResolvedPolicy {
                    digest_sha256: rp.digest_sha256(),
                    runtime: rp,
                    source: PolicySource {
                        kind: PolicySourceKind::BundleDir,
                        path: Some(p.display().to_string()),
                    },
                });
            }
        }

        // Compile legacy config (always available as fail-closed-compatible fallback).
        let legacy_runtime = runtime_policy_from_legacy(&legacy.config, deployment_env);
        let legacy_resolved = ResolvedPolicy {
            digest_sha256: legacy_runtime.digest_sha256(),
            runtime: legacy_runtime,
            source: PolicySource {
                kind: match legacy.source.kind {
                    crate::policy_config::PolicySourceKind::OverrideFile
                    | crate::policy_config::PolicySourceKind::EnvFile
                    | crate::policy_config::PolicySourceKind::FallbackFile => {
                        PolicySourceKind::LegacyConfigFile
                    }
                    crate::policy_config::PolicySourceKind::Defaults => PolicySourceKind::Defaults,
                },
                path: legacy.source.path.clone(),
            },
        };

        // Fail-closed ambiguity: if multiple bundles are loaded, they must not conflict in applicability.
        // For Phase 1, we treat loaded bundles as a single global policy (selectors must include "*"
        // or be irrelevant). Tenant/env selection is implemented later when multiple bundles are introduced.
        // Here we enforce: at most 1 bundle can be active for a deployment env.
        if loaded.len() > 1 {
            return Err(format!(
                "Invalid policy configuration: refusing to start — multiple policy bundles matched (count={})",
                loaded.len()
            ));
        }

        Ok(Self {
            deployment_env,
            policies: Arc::new(loaded),
            legacy_fallback: Arc::new(legacy_resolved),
        })
    }

    pub fn resolve_for_request(&self, tenant_id: &str) -> &ResolvedPolicy {
        // Phase 1: bundle selection is global; future extension uses tenant/env selectors.
        // We still include tenant_id for API compatibility and to preserve the invariant
        // that tenant context participates in policy resolution deterministically.
        let _ = tenant_id;
        self.policies.first().unwrap_or(&self.legacy_fallback)
    }

    pub fn enforce_ingest_for_request(
        &self,
        tenant_id: &str,
        event: &EvidenceEvent,
        ledger: &dyn crate::policy_engine::LedgerView,
    ) -> Result<(), PolicyViolation> {
        let p = self.resolve_for_request(tenant_id);
        enforce_ingest(&p.runtime, event, ledger)
    }

    pub fn deployment_env(&self) -> GovaiEnvironment {
        self.deployment_env
    }
}

fn load_bundle_doc(doc: &GovaiPolicyV1) -> Result<RuntimePolicy, String> {
    if doc.schema != "govai.policy.v1" {
        return Err(format!("unsupported policy schema: {}", doc.schema));
    }

    // Minimal semantic validation + normalization.
    let unknown = doc.ingest_rules.unknown_event_types.behavior.as_str();
    let unknown_behavior = unknown
        .parse::<UnknownEventTypeBehavior>()
        .map_err(|()| format!("invalid unknown_event_types.behavior: {unknown:?}"))?;

    // Interpret the v1 doc's `schema` and `gates` as a typed subset.
    let mut event_rules: BTreeMap<String, EventTypeRule> = BTreeMap::new();

    for (event_type, rule) in doc.ingest_rules.event_types.iter() {
        // Payload schema subset: expect `required_nonempty_strings` and `required_types`.
        let required_types = rule
            .schema
            .get("required_types")
            .cloned()
            .unwrap_or(serde_json::Value::Object(Default::default()));
        let required_nonempty_strings = rule
            .schema
            .get("required_nonempty_strings")
            .cloned()
            .unwrap_or(serde_json::Value::Array(vec![]));

        let mut req: BTreeMap<String, FieldType> = BTreeMap::new();
        if let Some(map) = required_types.as_object() {
            for (k, v) in map.iter() {
                let t = v.as_str().unwrap_or("");
                let ft = match t {
                    "string" => FieldType::String,
                    "number" => FieldType::Number,
                    "boolean" => FieldType::Boolean,
                    _ => {
                        return Err(format!(
                            "invalid field type for event_type={event_type} field={k}: {t:?}"
                        ))
                    }
                };
                req.insert(k.clone(), ft);
            }
        } else {
            return Err(format!(
                "invalid schema.required_types for event_type={event_type}: must be object"
            ));
        }

        let mut nes: BTreeSet<String> = BTreeSet::new();
        if let Some(arr) = required_nonempty_strings.as_array() {
            for v in arr.iter() {
                let s = v.as_str().unwrap_or("").trim();
                if !s.is_empty() {
                    nes.insert(s.to_string());
                }
            }
        } else {
            return Err(format!(
                "invalid schema.required_nonempty_strings for event_type={event_type}: must be array"
            ));
        }

        let schema = PayloadSchema {
            required: req,
            required_nonempty_strings: nes,
        };

        let mut gates: Vec<Gate> = Vec::new();
        for g in rule.gates.iter().cloned() {
            let gate: Gate = serde_json::from_value(g)
                .map_err(|e| format!("invalid gate for event_type={event_type}: {e}"))?;
            gates.push(gate);
        }

        event_rules.insert(
            event_type.to_string(),
            EventTypeRule {
                payload_schema: schema,
                gates,
            },
        );
    }

    Ok(RuntimePolicy {
        policy_id: doc.policy_id.clone(),
        version: doc.version.clone(),
        unknown_event_types: unknown_behavior,
        event_rules,
    })
}

fn runtime_policy_from_legacy(
    cfg: &PolicyConfig,
    deployment_env: GovaiEnvironment,
) -> RuntimePolicy {
    let unknown = match deployment_env {
        GovaiEnvironment::Dev => UnknownEventTypeBehavior::Allow,
        GovaiEnvironment::Staging | GovaiEnvironment::Prod => UnknownEventTypeBehavior::Reject,
    };

    // Build a declarative representation of the current hardcoded gates.
    // This keeps backward compatibility while moving enforcement into a generic evaluator.
    let mut event_rules: BTreeMap<String, EventTypeRule> = BTreeMap::new();

    // data_registered
    event_rules.insert(
        "data_registered".to_string(),
        EventTypeRule {
            payload_schema: PayloadSchema {
                required: BTreeMap::new(),
                required_nonempty_strings: BTreeSet::from([
                    "ai_system_id".to_string(),
                    "dataset_id".to_string(),
                    "dataset".to_string(),
                    "dataset_fingerprint".to_string(),
                    "dataset_governance_id".to_string(),
                    "dataset_governance_commitment".to_string(),
                    "dataset_version".to_string(),
                    "source".to_string(),
                    "intended_use".to_string(),
                    "limitations".to_string(),
                    "quality_summary".to_string(),
                    "governance_status".to_string(),
                ]),
            },
            gates: vec![],
        },
    );

    // model_trained
    let mut mt_req: BTreeSet<String> = BTreeSet::new();
    mt_req.insert("ai_system_id".to_string());
    mt_req.insert("dataset_id".to_string());
    mt_req.insert("model_version_id".to_string());
    let mut mt_gates: Vec<Gate> = Vec::new();
    if cfg.block_if_missing_evidence {
        mt_gates.push(Gate::RequiresEventType {
            event_type: "data_registered".to_string(),
            code: "missing_data_registered".to_string(),
            message:
                "policy_violation: model_trained requires prior data_registered for the same run_id"
                    .to_string(),
        });
    }
    event_rules.insert(
        "model_trained".to_string(),
        EventTypeRule {
            payload_schema: PayloadSchema {
                required: BTreeMap::new(),
                required_nonempty_strings: mt_req,
            },
            gates: mt_gates,
        },
    );

    // evaluation_reported
    let mut er_types: BTreeMap<String, FieldType> = BTreeMap::new();
    er_types.insert("value".to_string(), FieldType::Number);
    er_types.insert("threshold".to_string(), FieldType::Number);
    er_types.insert("passed".to_string(), FieldType::Boolean);
    let mut er_req: BTreeSet<String> = BTreeSet::new();
    er_req.insert("ai_system_id".to_string());
    er_req.insert("dataset_id".to_string());
    er_req.insert("model_version_id".to_string());
    er_req.insert("metric".to_string());
    event_rules.insert(
        "evaluation_reported".to_string(),
        EventTypeRule {
            payload_schema: PayloadSchema {
                required: er_types,
                required_nonempty_strings: er_req,
            },
            gates: vec![],
        },
    );

    // risk_recorded
    let mut rr_types: BTreeMap<String, FieldType> = BTreeMap::new();
    rr_types.insert("severity".to_string(), FieldType::Number);
    rr_types.insert("likelihood".to_string(), FieldType::Number);
    let mut rr_req: BTreeSet<String> = BTreeSet::new();
    rr_req.extend([
        "ai_system_id".to_string(),
        "dataset_id".to_string(),
        "model_version_id".to_string(),
        "risk_id".to_string(),
        "assessment_id".to_string(),
        "dataset_governance_commitment".to_string(),
        "risk_class".to_string(),
        "status".to_string(),
        "mitigation".to_string(),
        "owner".to_string(),
    ]);
    event_rules.insert(
        "risk_recorded".to_string(),
        EventTypeRule {
            payload_schema: PayloadSchema {
                required: rr_types,
                required_nonempty_strings: rr_req,
            },
            gates: vec![],
        },
    );

    // risk_mitigated
    let mut rm_req: BTreeSet<String> = BTreeSet::new();
    rm_req.extend([
        "ai_system_id".to_string(),
        "dataset_id".to_string(),
        "model_version_id".to_string(),
        "risk_id".to_string(),
        "assessment_id".to_string(),
        "dataset_governance_commitment".to_string(),
        "status".to_string(),
        "mitigation".to_string(),
    ]);
    event_rules.insert(
        "risk_mitigated".to_string(),
        EventTypeRule {
            payload_schema: PayloadSchema {
                required: BTreeMap::new(),
                required_nonempty_strings: rm_req,
            },
            gates: vec![],
        },
    );

    // risk_reviewed
    let mut rrev_req: BTreeSet<String> = BTreeSet::new();
    rrev_req.extend([
        "ai_system_id".to_string(),
        "dataset_id".to_string(),
        "model_version_id".to_string(),
        "risk_id".to_string(),
        "assessment_id".to_string(),
        "dataset_governance_commitment".to_string(),
        "reviewer".to_string(),
        "justification".to_string(),
    ]);
    let rrev_gates = vec![Gate::RequiresDecisionEnum {
        field: "decision".to_string(),
        allowed: vec!["approve".to_string(), "reject".to_string()],
        code: "schema_invalid".to_string(),
        message: "policy_violation: risk_reviewed payload must include decision(approve|reject)"
            .to_string(),
    }];
    event_rules.insert(
        "risk_reviewed".to_string(),
        EventTypeRule {
            payload_schema: PayloadSchema {
                required: BTreeMap::new(),
                required_nonempty_strings: rrev_req,
            },
            gates: rrev_gates,
        },
    );

    // human_approved
    let mut ha_req: BTreeSet<String> = BTreeSet::new();
    ha_req.extend([
        "scope".to_string(),
        "decision".to_string(),
        "approver".to_string(),
        "justification".to_string(),
        "assessment_id".to_string(),
        "risk_id".to_string(),
        "dataset_governance_commitment".to_string(),
        "ai_system_id".to_string(),
        "dataset_id".to_string(),
        "model_version_id".to_string(),
    ]);
    let mut ha_gates: Vec<Gate> = vec![
        Gate::RequiresScope {
            scope: "model_promoted".to_string(),
            code: "schema_invalid".to_string(),
            message: "policy_violation: human_approved payload must include scope=model_promoted"
                .to_string(),
        },
        Gate::RequiresDecisionEnum {
            field: "decision".to_string(),
            allowed: vec!["approve".to_string(), "reject".to_string()],
            code: "schema_invalid".to_string(),
            message:
                "policy_violation: human_approved payload must include decision(approve|reject)"
                    .to_string(),
        },
    ];

    if cfg.enforce_approver_allowlist {
        let allow = effective_approver_allowlist(cfg);
        ha_gates.push(Gate::RequiresApproverAllowlist {
            field: "approver".to_string(),
            allowlist: allow,
            code: "approver_not_allowlisted".to_string(),
            message_prefix: "policy_violation: human_approved approver".to_string(),
        });
    }
    if cfg.require_risk_review_for_approval {
        ha_gates.push(Gate::RequiresRiskReviewedApproved {
            code: "missing_risk_review_for_approval".to_string(),
            message:
                "policy_violation: human_approved requires prior risk_reviewed decision=approve with matching assessment_id/risk_id/dataset_governance_commitment"
                    .to_string(),
            linkage_keys: vec![
                "assessment_id".to_string(),
                "risk_id".to_string(),
                "dataset_governance_commitment".to_string(),
                "ai_system_id".to_string(),
                "dataset_id".to_string(),
                "model_version_id".to_string(),
            ],
        });
    }
    event_rules.insert(
        "human_approved".to_string(),
        EventTypeRule {
            payload_schema: PayloadSchema {
                required: BTreeMap::new(),
                required_nonempty_strings: ha_req,
            },
            gates: ha_gates,
        },
    );

    // model_promoted
    let mut mp_req: BTreeSet<String> = BTreeSet::new();
    mp_req.extend([
        "artifact_path".to_string(),
        "promotion_reason".to_string(),
        "assessment_id".to_string(),
        "risk_id".to_string(),
        "dataset_governance_commitment".to_string(),
        "ai_system_id".to_string(),
        "dataset_id".to_string(),
        "model_version_id".to_string(),
    ]);
    let mut mp_gates: Vec<Gate> = Vec::new();
    if cfg.require_passed_evaluation_for_promotion {
        mp_gates.push(Gate::RequiresPassedEvaluation {
            code: "missing_passed_evaluation_for_promotion".to_string(),
            message:
                "policy_violation: model_promoted requires prior evaluation_reported with passed=true"
                    .to_string(),
        });
    }
    if cfg.require_risk_review_for_promotion {
        mp_gates.push(Gate::RequiresRiskReviewedApproved {
            code: "missing_risk_review_for_promotion".to_string(),
            message:
                "policy_violation: model_promoted blocked by missing or rejected risk_reviewed (requires decision=approve with matching assessment_id/risk_id/dataset_governance_commitment/ai_system_id/dataset_id/model_version_id)"
                    .to_string(),
            linkage_keys: vec![
                "assessment_id".to_string(),
                "risk_id".to_string(),
                "dataset_governance_commitment".to_string(),
                "ai_system_id".to_string(),
                "dataset_id".to_string(),
                "model_version_id".to_string(),
            ],
        });
    }
    if cfg.require_approval {
        mp_req.insert("approved_human_event_id".to_string());
        mp_gates.push(Gate::RequiresHumanApprovedForPromotion {
            code: "missing_human_approval_for_promotion".to_string(),
            message:
                "policy_violation: model_promoted requires prior human_approved decision=approve with matching assessment_id/risk_id/dataset_governance_commitment/ai_system_id/dataset_id/model_version_id and approved_human_event_id"
                    .to_string(),
            linkage_keys: vec![
                "assessment_id".to_string(),
                "risk_id".to_string(),
                "dataset_governance_commitment".to_string(),
                "ai_system_id".to_string(),
                "dataset_id".to_string(),
                "model_version_id".to_string(),
            ],
            approved_event_id_field: "approved_human_event_id".to_string(),
        });
    }
    event_rules.insert(
        "model_promoted".to_string(),
        EventTypeRule {
            payload_schema: PayloadSchema {
                required: BTreeMap::new(),
                required_nonempty_strings: mp_req,
            },
            gates: mp_gates,
        },
    );

    RuntimePolicy {
        policy_id: "legacy-policy-config".to_string(),
        version: crate::govai_environment::policy_version_for(deployment_env).to_string(),
        unknown_event_types: unknown,
        event_rules,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::policy_engine::LedgerView;

    struct MemLedger {
        events: Vec<EvidenceEvent>,
    }
    impl LedgerView for MemLedger {
        fn iter_events_for_run<'a>(
            &'a self,
            run_id: &'a str,
        ) -> Box<dyn Iterator<Item = EvidenceEvent> + 'a> {
            Box::new(
                self.events
                    .iter()
                    .cloned()
                    .filter(move |e| e.run_id == run_id),
            )
        }
    }

    fn mk_event(event_type: &str, payload: serde_json::Value) -> EvidenceEvent {
        EvidenceEvent {
            event_id: "e".to_string(),
            event_type: event_type.to_string(),
            ts_utc: "t".to_string(),
            actor: "a".to_string(),
            system: "s".to_string(),
            run_id: "r".to_string(),
            environment: Some("dev".to_string()),
            payload,
            parent_run_id: None,
            root_run_id: None,
            delegated_from_event_id: None,
            agent_id: None,
            agent_role: None,
            delegation_reason: None,
        }
    }

    #[test]
    fn legacy_policy_rejects_unknown_event_types_in_prod() {
        let cfg = PolicyConfig::default();
        let p = runtime_policy_from_legacy(&cfg, GovaiEnvironment::Prod);
        let ledger = MemLedger { events: vec![] };
        let ev = mk_event("some_new_event", serde_json::json!({}));
        let store = ResolvedPolicy {
            runtime: p,
            digest_sha256: "x".to_string(),
            source: PolicySource {
                kind: PolicySourceKind::Defaults,
                path: None,
            },
        };
        let s = PolicyStore {
            deployment_env: GovaiEnvironment::Prod,
            policies: Arc::new(vec![]),
            legacy_fallback: Arc::new(store),
        };
        let err = s
            .enforce_ingest_for_request("tenant", &ev, &ledger)
            .unwrap_err();
        assert_eq!(err.code, "unknown_event_type");
    }
}
