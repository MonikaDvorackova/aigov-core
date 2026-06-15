use crate::policy::PolicyViolation;
use crate::schema::EvidenceEvent;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UnknownEventTypeBehavior {
    Allow,
    Reject,
}

impl std::str::FromStr for UnknownEventTypeBehavior {
    type Err = ();

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.trim().to_ascii_lowercase().as_str() {
            "allow" => Ok(Self::Allow),
            "reject" => Ok(Self::Reject),
            _ => Err(()),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FieldType {
    String,
    Number,
    Boolean,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PayloadSchema {
    /// Fields required to be present and of the declared type.
    pub required: BTreeMap<String, FieldType>,
    /// Fields required to be present and non-empty strings (stronger than `FieldType::String`).
    #[serde(default)]
    pub required_nonempty_strings: BTreeSet<String>,
}

impl PayloadSchema {
    pub fn validate(&self, payload: &serde_json::Value) -> Result<(), PolicyViolation> {
        let obj = payload.as_object().ok_or_else(|| PolicyViolation {
            code: "schema_invalid".to_string(),
            message: "policy_violation: payload must be a JSON object".to_string(),
        })?;

        for (k, t) in self.required.iter() {
            let Some(v) = obj.get(k) else {
                return Err(PolicyViolation {
                    code: "schema_invalid".to_string(),
                    message: format!("policy_violation: payload missing required field {k}"),
                });
            };
            let ok = match t {
                FieldType::String => v.as_str().is_some(),
                FieldType::Number => v.as_f64().is_some(),
                FieldType::Boolean => v.as_bool().is_some(),
            };
            if !ok {
                return Err(PolicyViolation {
                    code: "schema_invalid".to_string(),
                    message: format!("policy_violation: payload field {k} has wrong type"),
                });
            }
        }

        for k in self.required_nonempty_strings.iter() {
            let Some(v) = obj.get(k) else {
                return Err(PolicyViolation {
                    code: "schema_invalid".to_string(),
                    message: format!("policy_violation: payload missing required field {k}"),
                });
            };
            let ok = v.as_str().map(|s| !s.trim().is_empty()).unwrap_or(false);
            if !ok {
                return Err(PolicyViolation {
                    code: "schema_invalid".to_string(),
                    message: format!(
                        "policy_violation: payload field {k} must be a non-empty string"
                    ),
                });
            }
        }

        Ok(())
    }
}

/// Cross-event deterministic gate types (Phase 1).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
pub enum Gate {
    /// Require that a prior event type exists for the same run_id.
    RequiresEventType {
        event_type: String,
        code: String,
        message: String,
    },

    /// Require a prior `evaluation_reported` with `passed=true` for the same run_id.
    RequiresPassedEvaluation { code: String, message: String },

    /// Require a prior `risk_reviewed` with decision=approve and matching linkage keys.
    RequiresRiskReviewedApproved {
        code: String,
        message: String,
        linkage_keys: Vec<String>,
    },

    /// Require a prior `human_approved` with decision=approve and matching linkage keys,
    /// and that its `event_id` matches payload field `approved_human_event_id`.
    RequiresHumanApprovedForPromotion {
        code: String,
        message: String,
        linkage_keys: Vec<String>,
        approved_event_id_field: String,
    },

    /// Require payload field `scope` equals a constant.
    RequiresScope {
        scope: String,
        code: String,
        message: String,
    },

    /// Require that payload field `decision` is one of the allowed values.
    RequiresDecisionEnum {
        field: String,
        allowed: Vec<String>,
        code: String,
        message: String,
    },

    /// Require that payload field `approver` is in a configured allowlist (case-insensitive).
    RequiresApproverAllowlist {
        field: String,
        allowlist: Vec<String>,
        code: String,
        message_prefix: String,
    },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EventTypeRule {
    pub payload_schema: PayloadSchema,
    #[serde(default)]
    pub gates: Vec<Gate>,
}

#[derive(Debug, Clone)]
pub struct RuntimePolicy {
    pub policy_id: String,
    pub version: String,
    pub unknown_event_types: UnknownEventTypeBehavior,
    pub event_rules: BTreeMap<String, EventTypeRule>,
}

impl RuntimePolicy {
    pub fn digest_sha256(&self) -> String {
        // Deterministic digest over canonical JSON representation of this runtime policy.
        // Note: this is an internal digest (used for drift detection and exports). Signed-policy
        // payload digests will be defined in the signed policy module.
        let v = serde_json::json!({
            "schema": "govai.runtime_policy_digest.v1",
            "policy_id": self.policy_id,
            "version": self.version,
            "unknown_event_types": match self.unknown_event_types {
                UnknownEventTypeBehavior::Allow => "allow",
                UnknownEventTypeBehavior::Reject => "reject",
            },
            "event_rules": self.event_rules
        });
        let bytes = serde_json::to_vec(&v).expect("runtime policy serde");
        let mut h = Sha256::new();
        h.update(bytes);
        hex::encode(h.finalize())
    }
}

pub trait LedgerView {
    fn iter_events_for_run<'a>(
        &'a self,
        run_id: &'a str,
    ) -> Box<dyn Iterator<Item = EvidenceEvent> + 'a>;
}

/// Evaluate ingest-time policy (schema + cross-event gates).
pub fn enforce_ingest(
    policy: &RuntimePolicy,
    event: &EvidenceEvent,
    ledger: &dyn LedgerView,
) -> Result<(), PolicyViolation> {
    let Some(rule) = policy.event_rules.get(event.event_type.as_str()) else {
        return match policy.unknown_event_types {
            UnknownEventTypeBehavior::Allow => Ok(()),
            UnknownEventTypeBehavior::Reject => Err(PolicyViolation {
                code: "unknown_event_type".to_string(),
                message: format!(
                    "policy_violation: unknown event_type={}; refusing by policy",
                    event.event_type
                ),
            }),
        };
    };

    rule.payload_schema.validate(&event.payload)?;

    for gate in rule.gates.iter() {
        enforce_gate(gate, event, ledger)?;
    }

    Ok(())
}

fn enforce_gate(
    gate: &Gate,
    event: &EvidenceEvent,
    ledger: &dyn LedgerView,
) -> Result<(), PolicyViolation> {
    match gate {
        Gate::RequiresEventType {
            event_type,
            code,
            message,
        } => {
            let ok = ledger
                .iter_events_for_run(&event.run_id)
                .any(|e| e.event_type == *event_type);
            if ok {
                Ok(())
            } else {
                Err(PolicyViolation {
                    code: code.clone(),
                    message: message.clone(),
                })
            }
        }
        Gate::RequiresPassedEvaluation { code, message } => {
            let ok = ledger.iter_events_for_run(&event.run_id).any(|e| {
                if e.event_type != "evaluation_reported" {
                    return false;
                }
                e.payload
                    .get("passed")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(false)
            });
            if ok {
                Ok(())
            } else {
                Err(PolicyViolation {
                    code: code.clone(),
                    message: message.clone(),
                })
            }
        }
        Gate::RequiresRiskReviewedApproved {
            code,
            message,
            linkage_keys,
        } => {
            let ok = ledger.iter_events_for_run(&event.run_id).any(|e| {
                if e.event_type != "risk_reviewed" {
                    return false;
                }
                let decision = e
                    .payload
                    .get("decision")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                if decision != "approve" {
                    return false;
                }
                linkage_keys.iter().all(|k| {
                    let a = event.payload.get(k).and_then(|v| v.as_str()).unwrap_or("");
                    let b = e.payload.get(k).and_then(|v| v.as_str()).unwrap_or("");
                    !a.trim().is_empty() && a == b
                })
            });
            if ok {
                Ok(())
            } else {
                Err(PolicyViolation {
                    code: code.clone(),
                    message: message.clone(),
                })
            }
        }
        Gate::RequiresHumanApprovedForPromotion {
            code,
            message,
            linkage_keys,
            approved_event_id_field,
        } => {
            let want = event
                .payload
                .get(approved_event_id_field)
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim()
                .to_string();
            if want.is_empty() {
                return Err(PolicyViolation {
                    code: code.clone(),
                    message: message.clone(),
                });
            }

            let ok = ledger.iter_events_for_run(&event.run_id).any(|e| {
                if e.event_type != "human_approved" || e.event_id != want {
                    return false;
                }
                let scope_ok = e
                    .payload
                    .get("scope")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    == "model_promoted";
                let decision_ok = e
                    .payload
                    .get("decision")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    == "approve";
                if !(scope_ok && decision_ok) {
                    return false;
                }
                linkage_keys.iter().all(|k| {
                    let a = event.payload.get(k).and_then(|v| v.as_str()).unwrap_or("");
                    let b = e.payload.get(k).and_then(|v| v.as_str()).unwrap_or("");
                    !a.trim().is_empty() && a == b
                })
            });
            if ok {
                Ok(())
            } else {
                Err(PolicyViolation {
                    code: code.clone(),
                    message: message.clone(),
                })
            }
        }
        Gate::RequiresScope {
            scope,
            code,
            message,
        } => {
            let got = event
                .payload
                .get("scope")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            if got == scope {
                Ok(())
            } else {
                Err(PolicyViolation {
                    code: code.clone(),
                    message: message.clone(),
                })
            }
        }
        Gate::RequiresDecisionEnum {
            field,
            allowed,
            code,
            message,
        } => {
            let got = event.payload.get(field).and_then(|v| v.as_str());
            let ok = got.is_some_and(|s| allowed.iter().any(|a| a == s));
            if ok {
                Ok(())
            } else {
                Err(PolicyViolation {
                    code: code.clone(),
                    message: message.clone(),
                })
            }
        }
        Gate::RequiresApproverAllowlist {
            field,
            allowlist,
            code,
            message_prefix,
        } => {
            let got = event
                .payload
                .get(field)
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .trim()
                .to_ascii_lowercase();
            if got.is_empty() {
                return Err(PolicyViolation {
                    code: "schema_invalid".to_string(),
                    message: format!("policy_violation: {field} must be a non-empty string"),
                });
            }
            let ok = allowlist.iter().any(|a| a == &got);
            if ok {
                Ok(())
            } else {
                Err(PolicyViolation {
                    code: code.clone(),
                    message: format!("{message_prefix} '{got}'"),
                })
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::UnknownEventTypeBehavior;
    use std::str::FromStr;

    #[test]
    fn unknown_event_type_behavior_from_str() {
        assert_eq!(
            UnknownEventTypeBehavior::from_str("allow").unwrap(),
            UnknownEventTypeBehavior::Allow
        );
        assert_eq!(
            UnknownEventTypeBehavior::from_str("REJECT").unwrap(),
            UnknownEventTypeBehavior::Reject
        );
        assert!(UnknownEventTypeBehavior::from_str("nope").is_err());
    }
}
