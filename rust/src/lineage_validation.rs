//! Lineage integrity validation for exports and replay.

use crate::lineage_projection::{project_lineage_records, LineageEventRecord};
use crate::schema::EvidenceEvent;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LineageIssue {
    pub code: String,
    pub message: String,
    pub severity: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct LineageValidationReport {
    pub errors: Vec<LineageIssue>,
    pub warnings: Vec<LineageIssue>,
    pub root_run_id_consistent: bool,
    pub delegation_cycle_detected: bool,
    pub orphaned_delegated_runs: Vec<String>,
    pub missing_parent_runs: Vec<String>,
    pub invalid_delegation_transitions: Vec<String>,
}

impl LineageValidationReport {
    pub fn push_error(&mut self, code: impl Into<String>, message: impl Into<String>) {
        self.errors.push(LineageIssue {
            code: code.into(),
            message: message.into(),
            severity: "error".to_string(),
        });
    }

    pub fn push_warning(&mut self, code: impl Into<String>, message: impl Into<String>) {
        self.warnings.push(LineageIssue {
            code: code.into(),
            message: message.into(),
            severity: "warning".to_string(),
        });
    }

    pub fn is_ok(&self) -> bool {
        self.errors.is_empty() && !self.delegation_cycle_detected
    }
}

pub fn validate_lineage_for_run(
    run_id: &str,
    events: &[EvidenceEvent],
    known_run_ids: &HashSet<String>,
) -> LineageValidationReport {
    let records = project_lineage_records(events);
    validate_lineage_records(run_id, &records, known_run_ids)
}

pub fn validate_lineage_records(
    run_id: &str,
    records: &[LineageEventRecord],
    known_run_ids: &HashSet<String>,
) -> LineageValidationReport {
    let mut report = LineageValidationReport::default();
    let run_records: Vec<&LineageEventRecord> = records.iter().filter(|r| r.run_id == run_id).collect();

    if run_records.is_empty() {
        report.push_warning("no_lineage_records", format!("no events for run_id={run_id}"));
        return report;
    }

    // root_run_id consistency within run
    let roots: HashSet<String> = run_records
        .iter()
        .filter_map(|r| r.lineage.root_run_id.clone())
        .collect();
    report.root_run_id_consistent = roots.len() <= 1;
    if roots.len() > 1 {
        report.push_error(
            "inconsistent_root_run_id",
            format!("multiple root_run_id values in run {run_id}: {:?}", roots),
        );
    }

    let expected_root = roots.iter().next().cloned().unwrap_or_else(|| run_id.to_string());
    if !expected_root.is_empty() && expected_root != run_id {
        // child run may differ; warn if root points elsewhere without parent link
        let has_parent = run_records
            .iter()
            .any(|r| r.lineage.parent_run_id.is_some());
        if !has_parent {
            report.push_warning(
                "root_without_parent",
                format!("run {run_id} has root_run_id={expected_root} but no parent_run_id"),
            );
        }
    }

    // parent_run_id presence in known set
    for r in &run_records {
        if let Some(ref parent) = r.lineage.parent_run_id {
            if parent != run_id && !known_run_ids.contains(parent) {
                report
                    .missing_parent_runs
                    .push(parent.clone());
                report.push_warning(
                    "missing_parent_run",
                    format!("parent_run_id={parent} not present in export scope"),
                );
            }
        }
        if let Some(ref del_from) = r.lineage.delegated_from_event_id {
            let exists = records.iter().any(|x| x.event_id == *del_from);
            if !exists {
                report.push_warning(
                    "missing_delegated_from_event",
                    format!("delegated_from_event_id={del_from} not found in export"),
                );
            }
        }
    }

    // delegation run graph: parent_run -> child_run from agent_delegated
    let mut adj: HashMap<String, Vec<String>> = HashMap::new();
    let mut all_runs: HashSet<String> = HashSet::new();
    all_runs.insert(run_id.to_string());
    for r in records {
        all_runs.insert(r.run_id.clone());
        if let Some(ref child) = r.child_run_id {
            all_runs.insert(child.clone());
            let parent = r
                .lineage
                .parent_run_id
                .clone()
                .unwrap_or_else(|| r.run_id.clone());
            adj.entry(parent).or_default().push(child.clone());
        }
    }

    if has_cycle(&adj) {
        report.delegation_cycle_detected = true;
        report.push_error("delegation_cycle", "cyclic run delegation detected");
    }

    // orphaned delegated runs: child_run_id referenced but no events for that run in export
    for r in records {
        if let Some(ref child) = r.child_run_id {
            let child_has_events = records.iter().any(|x| x.run_id == *child);
            if !child_has_events {
                report.orphaned_delegated_runs.push(child.clone());
                report.push_warning(
                    "orphaned_delegated_run",
                    format!("child_run_id={child} has no events in export"),
                );
            }
        }
    }

    // invalid transitions: agent_delegated without agent_id
    for r in records {
        if r.event_type == "agent_delegated" {
            if r.lineage.agent_id.is_none() {
                report
                    .invalid_delegation_transitions
                    .push(r.event_id.clone());
                report.push_error(
                    "delegation_missing_agent_id",
                    format!("agent_delegated event {} missing agent_id", r.event_id),
                );
            }
            if r.child_run_id.is_none() {
                report
                    .invalid_delegation_transitions
                    .push(r.event_id.clone());
                report.push_error(
                    "delegation_missing_child_run",
                    format!("agent_delegated event {} missing child_run_id", r.event_id),
                );
            }
        }
    }

    report.missing_parent_runs.sort();
    report.missing_parent_runs.dedup();
    report.orphaned_delegated_runs.sort();
    report.orphaned_delegated_runs.dedup();

    report
}

fn has_cycle(adj: &HashMap<String, Vec<String>>) -> bool {
    let mut visiting: HashSet<String> = HashSet::new();
    let mut visited: HashSet<String> = HashSet::new();
    for start in adj.keys() {
        if dfs_cycle(start, adj, &mut visiting, &mut visited) {
            return true;
        }
    }
    false
}

fn dfs_cycle(
    node: &str,
    adj: &HashMap<String, Vec<String>>,
    visiting: &mut HashSet<String>,
    visited: &mut HashSet<String>,
) -> bool {
    if visiting.contains(node) {
        return true;
    }
    if visited.contains(node) {
        return false;
    }
    visiting.insert(node.to_string());
    if let Some(children) = adj.get(node) {
        for c in children {
            if dfs_cycle(c, adj, visiting, visited) {
                return true;
            }
        }
    }
    visiting.remove(node);
    visited.insert(node.to_string());
    false
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::schema::EvidenceEvent;
    use serde_json::json;

    #[test]
    fn detects_delegation_cycle() {
        let events = vec![
            EvidenceEvent {
                event_id: "d1".into(),
                event_type: "agent_delegated".into(),
                ts_utc: "2026-01-01T00:00:01Z".into(),
                actor: "a".into(),
                system: "s".into(),
                run_id: "run-a".into(),
                environment: None,
                payload: json!({"child_run_id": "run-b", "agent_id": "planner"}),
                parent_run_id: None,
                root_run_id: Some("run-a".into()),
                delegated_from_event_id: None,
                agent_id: Some("planner".into()),
                agent_role: Some("orchestrator".into()),
                delegation_reason: Some("specialist".into()),
            },
            EvidenceEvent {
                event_id: "d2".into(),
                event_type: "agent_delegated".into(),
                ts_utc: "2026-01-01T00:00:02Z".into(),
                actor: "a".into(),
                system: "s".into(),
                run_id: "run-b".into(),
                environment: None,
                payload: json!({"child_run_id": "run-a", "agent_id": "worker"}),
                parent_run_id: Some("run-a".into()),
                root_run_id: Some("run-a".into()),
                delegated_from_event_id: Some("d1".into()),
                agent_id: Some("worker".into()),
                agent_role: None,
                delegation_reason: None,
            },
        ];
        let known: HashSet<String> = ["run-a", "run-b"].into_iter().map(String::from).collect();
        let rep = validate_lineage_for_run("run-a", &events, &known);
        assert!(rep.delegation_cycle_detected);
    }
}
