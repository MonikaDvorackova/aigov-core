//! Validation of audit export inputs before governance replay.

use crate::bundle::{canonicalize_evidence_events, portable_evidence_digest_v1};
use crate::lineage_validation::validate_lineage_for_run;
use crate::schema::EvidenceEvent;
use serde::Serialize;
use serde_json::Value;
use std::collections::HashSet;

pub const EXPORT_SCHEMA_V1: &str = "aigov.audit_export.v1";

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct ValidationIssue {
    pub code: String,
    pub message: String,
    pub severity: String,
}

#[derive(Debug, Clone, Serialize, Default)]
pub struct ReplayValidationReport {
    pub errors: Vec<ValidationIssue>,
    pub warnings: Vec<ValidationIssue>,
    pub duplicate_event_ids: Vec<String>,
    pub event_ordering_ok: bool,
    pub chain_continuity_ok: bool,
    pub run_id_consistent: bool,
    pub events_content_sha256_ok: bool,
    pub lifecycle_transitions_ok: bool,
}

impl ReplayValidationReport {
    pub fn push_error(&mut self, code: impl Into<String>, message: impl Into<String>) {
        self.errors.push(ValidationIssue {
            code: code.into(),
            message: message.into(),
            severity: "error".to_string(),
        });
    }

    pub fn push_warning(&mut self, code: impl Into<String>, message: impl Into<String>) {
        self.warnings.push(ValidationIssue {
            code: code.into(),
            message: message.into(),
            severity: "warning".to_string(),
        });
    }

    pub fn is_ok(&self) -> bool {
        self.errors.is_empty()
    }
}

pub fn export_run_id(export: &Value) -> Option<String> {
    export
        .get("run")
        .and_then(|r| r.get("run_id"))
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
}

pub fn parse_evidence_events(export: &Value, report: &mut ReplayValidationReport) -> Vec<EvidenceEvent> {
    let Some(arr) = export.get("evidence_events").and_then(|v| v.as_array()) else {
        report.push_error("missing_evidence_events", "evidence_events must be an array");
        return Vec::new();
    };
    let mut out = Vec::with_capacity(arr.len());
    for (i, item) in arr.iter().enumerate() {
        match serde_json::from_value::<EvidenceEvent>(item.clone()) {
            Ok(ev) => out.push(ev),
            Err(e) => report.push_error(
                "invalid_evidence_event",
                format!("evidence_events[{i}] is not a valid evidence event: {e}"),
            ),
        }
    }
    out
}

pub fn validate_schema_version(export: &Value, report: &mut ReplayValidationReport) {
    let schema = export
        .get("schema_version")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .trim();
    if schema != EXPORT_SCHEMA_V1 {
        report.push_error(
            "unsupported_schema_version",
            format!("expected {EXPORT_SCHEMA_V1}, got {schema:?}"),
        );
    }
}

pub fn validate_run_id_consistency(
    run_id: &str,
    events: &[EvidenceEvent],
    report: &mut ReplayValidationReport,
) {
    let mut ok = true;
    for ev in events {
        if ev.run_id.trim() != run_id {
            ok = false;
            report.push_error(
                "inconsistent_run_id",
                format!(
                    "event {} has run_id {:?}, expected {:?}",
                    ev.event_id, ev.run_id, run_id
                ),
            );
        }
    }
    report.run_id_consistent = ok;
}

pub fn validate_duplicate_event_ids(events: &[EvidenceEvent], report: &mut ReplayValidationReport) {
    let mut seen = HashSet::new();
    let mut dups = Vec::new();
    for ev in events {
        if !seen.insert(ev.event_id.clone()) {
            dups.push(ev.event_id.clone());
        }
    }
    if !dups.is_empty() {
        dups.sort();
        report.duplicate_event_ids = dups.clone();
        report.push_error(
            "duplicate_event_id",
            format!("duplicate event_id values: {}", dups.join(", ")),
        );
    }
}

fn event_ids_in_export_order(events: &[EvidenceEvent]) -> Vec<String> {
    events.iter().map(|e| e.event_id.clone()).collect()
}

fn event_ids_in_stable_order(events: &[EvidenceEvent]) -> Vec<String> {
    let mut sorted = events.to_vec();
    sorted.sort_by(event_stable_cmp);
    sorted.iter().map(|e| e.event_id.clone()).collect()
}

fn event_ids_in_log_chain_order(export: &Value) -> Option<Vec<String>> {
    let chain = export
        .get("evidence_hashes")
        .and_then(|h| h.get("log_chain"))
        .and_then(|v| v.as_array())?;
    let ids: Vec<String> = chain
        .iter()
        .filter_map(|row| row.get("event_id").and_then(|v| v.as_str()))
        .map(|s| s.to_string())
        .collect();
    if ids.is_empty() {
        return None;
    }
    Some(ids)
}

pub fn validate_event_ordering(
    events: &[EvidenceEvent],
    export: &Value,
    report: &mut ReplayValidationReport,
) {
    if events.is_empty() {
        report.event_ordering_ok = true;
        return;
    }
    let export_order = event_ids_in_export_order(events);
    let stable_order = event_ids_in_stable_order(events);
    let mut ok = export_order == stable_order;

    if let Some(chain_order) = event_ids_in_log_chain_order(export) {
        if chain_order != export_order {
            ok = false;
            report.push_error(
                "event_order_mismatch_log_chain",
                "evidence_events order does not match evidence_hashes.log_chain order",
            );
        }
    }

    if export_order != stable_order {
        ok = false;
        report.push_error(
            "reordered_events",
            "evidence_events are not in deterministic stable order (ts_utc, event_type, event_id)",
        );
    }

    report.event_ordering_ok = ok;
}

pub fn validate_chain_continuity(export: &Value, report: &mut ReplayValidationReport) {
    let Some(chain) = export
        .get("evidence_hashes")
        .and_then(|h| h.get("log_chain"))
        .and_then(|v| v.as_array())
    else {
        report.push_warning(
            "missing_log_chain",
            "evidence_hashes.log_chain missing; skipping chain continuity check",
        );
        report.chain_continuity_ok = true;
        return;
    };

    if chain.is_empty() {
        report.chain_continuity_ok = true;
        return;
    }

    let mut ok = true;
    for (i, row) in chain.iter().enumerate() {
        let record_hash = row
            .get("record_hash")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim();
        if record_hash.is_empty() {
            ok = false;
            report.push_error(
                "chain_missing_record_hash",
                format!("log_chain[{i}] missing record_hash"),
            );
            continue;
        }
        let prev = row.get("prev_hash");
        if i == 0 {
            let prev_s = prev.and_then(|v| v.as_str()).unwrap_or("").trim();
            if !prev_s.is_empty() && prev_s != "null" {
                ok = false;
                report.push_error(
                    "chain_invalid_genesis",
                    "first log_chain row must have empty prev_hash",
                );
            }
            continue;
        }
        let prev_s = prev
            .and_then(|v| v.as_str())
            .map(|s| s.trim().to_string())
            .unwrap_or_default();
        let prior_hash = chain[i - 1]
            .get("record_hash")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_string();
        if prev_s != prior_hash {
            ok = false;
            report.push_error(
                "chain_break",
                format!(
                    "log_chain[{i}] prev_hash does not link to prior record_hash (broken chain)"
                ),
            );
        }
    }
    report.chain_continuity_ok = ok;
}

pub fn validate_events_content_sha256(
    run_id: &str,
    events: &[EvidenceEvent],
    export: &Value,
    report: &mut ReplayValidationReport,
) {
    let declared = export
        .get("evidence_hashes")
        .and_then(|h| h.get("events_content_sha256"))
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_lowercase())
        .unwrap_or_default();
    if declared.len() != 64 {
        report.push_error(
            "invalid_events_content_sha256",
            "evidence_hashes.events_content_sha256 must be 64 hex chars",
        );
        report.events_content_sha256_ok = false;
        return;
    }
    let canonical = canonicalize_evidence_events(events.to_vec());
    let recomputed = portable_evidence_digest_v1(run_id, &canonical);
    if recomputed != declared {
        report.push_error(
            "events_content_sha256_mismatch",
            "declared events_content_sha256 does not match replay recomputation from evidence_events",
        );
        report.events_content_sha256_ok = false;
        return;
    }
    report.events_content_sha256_ok = true;
}

fn event_index_by_type(events: &[EvidenceEvent], event_type: &str) -> Option<usize> {
    events
        .iter()
        .enumerate()
        .find(|(_, e)| e.event_type == event_type)
        .map(|(i, _)| i)
}

pub fn validate_lifecycle_transitions(events: &[EvidenceEvent], report: &mut ReplayValidationReport) {
    let mut ok = true;
    let ordered = {
        let mut v = events.to_vec();
        v.sort_by(event_stable_cmp);
        v
    };

    let human_idx = event_index_by_type(&ordered, "human_approved");
    let promote_idx = event_index_by_type(&ordered, "model_promoted");

    if let Some(pi) = promote_idx {
        match human_idx {
            None => {
                ok = false;
                report.push_error(
                    "missing_approval_evidence",
                    "model_promoted present without prior human_approved evidence",
                );
            }
            Some(hi) if hi > pi => {
                ok = false;
                report.push_error(
                    "invalid_lifecycle_transition",
                    "model_promoted occurs before human_approved in event ordering",
                );
            }
            Some(_) => {}
        }
    }

    if let Some(hi) = human_idx {
        let risk_idx = event_index_by_type(&ordered, "risk_reviewed");
        if risk_idx.is_none() {
            report.push_warning(
                "missing_risk_review",
                "human_approved recorded without risk_reviewed (policy may still block promotion)",
            );
        } else if let Some(ri) = risk_idx {
            if ri > hi {
                ok = false;
                report.push_error(
                    "invalid_lifecycle_transition",
                    "human_approved occurs before risk_reviewed",
                );
            }
        }
    }

    report.lifecycle_transitions_ok = ok;
}

pub fn run_export_validations(export: &Value) -> (ReplayValidationReport, Vec<EvidenceEvent>) {
    let mut report = ReplayValidationReport::default();
    validate_schema_version(export, &mut report);
    let run_id = export_run_id(export).unwrap_or_default();
    if run_id.is_empty() {
        report.push_error("missing_run_id", "run.run_id is required");
    }
    let events = parse_evidence_events(export, &mut report);
    if !run_id.is_empty() && !events.is_empty() {
        validate_run_id_consistency(&run_id, &events, &mut report);
        validate_duplicate_event_ids(&events, &mut report);
        validate_event_ordering(&events, export, &mut report);
        validate_chain_continuity(export, &mut report);
        validate_events_content_sha256(&run_id, &events, export, &mut report);
        validate_lifecycle_transitions(&events, &mut report);
        let mut known_runs: HashSet<String> = HashSet::new();
        known_runs.insert(run_id.clone());
        for ev in &events {
            known_runs.insert(ev.run_id.clone());
            let lin = ev.lineage();
            if let Some(p) = lin.parent_run_id {
                known_runs.insert(p);
            }
            if let Some(r) = lin.root_run_id {
                known_runs.insert(r);
            }
            if ev.event_type == "agent_delegated" {
                if let Some(c) = ev
                    .payload
                    .get("child_run_id")
                    .and_then(|v| v.as_str())
                {
                    known_runs.insert(c.to_string());
                }
            }
        }
        let lineage_report = validate_lineage_for_run(&run_id, &events, &known_runs);
        if lineage_report.delegation_cycle_detected {
            report.push_error("lineage_delegation_cycle", "delegation cycle in run lineage");
        }
        for err in &lineage_report.errors {
            report.push_error(format!("lineage_{}", err.code), err.message.clone());
        }
        for warn in &lineage_report.warnings {
            report.push_warning(format!("lineage_{}", warn.code), warn.message.clone());
        }
    }
    (report, events)
}

fn event_stable_cmp(a: &EvidenceEvent, b: &EvidenceEvent) -> std::cmp::Ordering {
    a.ts_utc
        .cmp(&b.ts_utc)
        .then_with(|| a.event_type.cmp(&b.event_type))
        .then_with(|| a.event_id.cmp(&b.event_id))
}

pub fn events_for_projection(events: &[EvidenceEvent]) -> Vec<EvidenceEvent> {
    let mut sorted = events.to_vec();
    sorted.sort_by(event_stable_cmp);
    sorted
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn minimal_export(events: Vec<Value>, chain: Vec<Value>) -> Value {
        json!({
            "ok": true,
            "schema_version": EXPORT_SCHEMA_V1,
            "policy_version": "p1",
            "environment": "dev",
            "run": { "run_id": "r1", "policy_version": "p1", "log_path": "l", "identifiers": {} },
            "evidence_hashes": {
                "bundle_sha256": "a".repeat(64),
                "events_content_sha256": "",
                "log_chain": chain,
            },
            "decision": { "verdict": "BLOCKED", "blocked_reasons": [] },
            "evidence_events": events,
        })
    }

    #[test]
    fn detects_duplicate_event_ids() {
        let ev = json!({
            "event_id": "e1",
            "event_type": "ai_discovery_reported",
            "ts_utc": "2026-01-01T00:00:01Z",
            "actor": "a",
            "system": "s",
            "run_id": "r1",
            "payload": { "openai": false, "transformers": false, "model_artifacts": false }
        });
        let export = minimal_export(vec![ev.clone(), ev], vec![]);
        let (report, _) = run_export_validations(&export);
        assert!(!report.duplicate_event_ids.is_empty());
    }
}
