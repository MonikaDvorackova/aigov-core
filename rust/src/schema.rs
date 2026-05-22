use serde::{Deserialize, Serialize};

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
}
