//! Extract multi-agent lineage records from evidence events (deterministic ordering).

use crate::schema::{EvidenceEvent, LineageFields};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LineageEventRecord {
    pub event_id: String,
    pub event_type: String,
    pub ts_utc: String,
    pub run_id: String,
    pub lineage: LineageFields,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub child_run_id: Option<String>,
}

/// Sort events for stable lineage replay (ts, event_id).
pub fn sort_events_for_lineage(events: &[EvidenceEvent]) -> Vec<EvidenceEvent> {
    let mut out = events.to_vec();
    out.sort_by(|a, b| {
        a.ts_utc
            .cmp(&b.ts_utc)
            .then_with(|| a.event_id.cmp(&b.event_id))
    });
    out
}

pub fn project_lineage_records(events: &[EvidenceEvent]) -> Vec<LineageEventRecord> {
    let ordered = sort_events_for_lineage(events);
    ordered
        .iter()
        .map(|ev| {
            let lineage = ev.lineage();
            let child_run_id = child_run_id_from_event(ev);
            LineageEventRecord {
                event_id: ev.event_id.clone(),
                event_type: ev.event_type.clone(),
                ts_utc: ev.ts_utc.clone(),
                run_id: ev.run_id.clone(),
                lineage,
                child_run_id,
            }
        })
        .collect()
}

fn child_run_id_from_event(ev: &EvidenceEvent) -> Option<String> {
    if ev.event_type == "agent_delegated" {
        return ev
            .payload
            .get("child_run_id")
            .and_then(|v| v.as_str())
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty());
    }
    None
}

pub fn summarize_run_lineage(records: &[LineageEventRecord], run_id: &str) -> Value {
    let mut root_run_id: Option<String> = None;
    let mut parent_run_id: Option<String> = None;
    for r in records {
        if r.run_id != run_id {
            continue;
        }
        if root_run_id.is_none() {
            root_run_id = r.lineage.root_run_id.clone();
        }
        if parent_run_id.is_none() {
            parent_run_id = r.lineage.parent_run_id.clone();
        }
    }
    let root = root_run_id.unwrap_or_else(|| run_id.to_string());
    json!({
        "run_id": run_id,
        "root_run_id": root,
        "parent_run_id": parent_run_id,
        "record_count": records.iter().filter(|r| r.run_id == run_id).count(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn lineage_defaults_root_to_run_id() {
        let ev = EvidenceEvent {
            event_id: "e1".into(),
            event_type: "ai_discovery_reported".into(),
            ts_utc: "2026-01-01T00:00:00Z".into(),
            actor: "a".into(),
            system: "s".into(),
            run_id: "run-a".into(),
            environment: None,
            payload: json!({}),
            parent_run_id: None,
            root_run_id: None,
            delegated_from_event_id: None,
            agent_id: None,
            agent_role: None,
            delegation_reason: None,
        };
        assert_eq!(ev.lineage().root_run_id.as_deref(), Some("run-a"));
    }
}
