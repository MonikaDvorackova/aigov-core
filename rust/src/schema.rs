use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone, Default, PartialEq, Eq)]
pub struct LineageFields {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parent_run_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub root_run_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub delegated_from_event_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub agent_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub agent_role: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub delegation_reason: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct EvidenceEvent {
    pub event_id: String,
    pub event_type: String,
    pub ts_utc: String,
    pub actor: String,
    pub system: String,
    pub run_id: String,
    /// Deployment tier (`dev` | `staging` | `prod`), stamped by the server on ingest.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub environment: Option<String>,
    pub payload: serde_json::Value,
    /// Multi-agent lineage (optional; append-only semantics, replay-stable).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parent_run_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub root_run_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub delegated_from_event_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub agent_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub agent_role: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub delegation_reason: Option<String>,
}

impl EvidenceEvent {
    #[inline]
    pub fn empty_lineage_fields() -> (
        Option<String>,
        Option<String>,
        Option<String>,
        Option<String>,
        Option<String>,
        Option<String>,
    ) {
        (None, None, None, None, None, None)
    }

    /// Resolved lineage for graph projection (top-level fields override payload keys).
    pub fn lineage(&self) -> LineageFields {
        let mut out = LineageFields {
            parent_run_id: self.parent_run_id.clone(),
            root_run_id: self.root_run_id.clone(),
            delegated_from_event_id: self.delegated_from_event_id.clone(),
            agent_id: self.agent_id.clone(),
            agent_role: self.agent_role.clone(),
            delegation_reason: self.delegation_reason.clone(),
        };
        let p = &self.payload;
        macro_rules! fill {
            ($field:ident) => {
                if out.$field.is_none() {
                    out.$field = p
                        .get(stringify!($field))
                        .and_then(|v| v.as_str())
                        .map(|s| s.trim().to_string())
                        .filter(|s| !s.is_empty());
                }
            };
        }
        fill!(parent_run_id);
        fill!(root_run_id);
        fill!(delegated_from_event_id);
        fill!(agent_id);
        fill!(agent_role);
        fill!(delegation_reason);
        if out.root_run_id.is_none() {
            out.root_run_id = Some(self.run_id.clone());
        }
        out
    }
}
