//! Canonical payload hashing, hash-chain verification, verdict derivation, delegation DAG analysis.

use chrono::{DateTime, Utc};
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};

pub const GENESIS_PREV: &str = "GENESIS_ALL_ZERO";
pub const DIGEST_CANONICAL: &str = "canonical_json_v1";
pub const DIGEST_LEGACY: &str = "legacy_pg_jsonb_text_sha256";

/// Stable JSON serialization: object keys sorted recursively; arrays preserve order.
pub fn canonical_json_string(v: &Value) -> String {
    serde_json::to_string(&canonicalize_value(v)).expect("canonical json")
}

fn canonicalize_value(v: &Value) -> Value {
    match v {
        Value::Object(map) => {
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort();
            let mut out = Map::new();
            for k in keys {
                out.insert(k.clone(), canonicalize_value(&map[k]));
            }
            Value::Object(out)
        }
        Value::Array(arr) => Value::Array(arr.iter().map(canonicalize_value).collect()),
        _ => v.clone(),
    }
}

pub fn canonical_payload_digest_hex(payload: &Value) -> String {
    let s = canonical_json_string(payload);
    let mut h = Sha256::new();
    h.update(s.as_bytes());
    hex::encode(h.finalize())
}

pub fn event_hash_hex(
    ledger_tenant_id: &str,
    run_id: &str,
    event_seq: i64,
    event_type: &str,
    canonical_payload_digest_hex: &str,
    previous_event_hash: &str,
    created_at_ms: i64,
) -> String {
    let mut h = Sha256::new();
    let line = format!(
        "{}|{}|{}|{}|{}|{}|{}",
        ledger_tenant_id,
        run_id,
        event_seq,
        event_type,
        canonical_payload_digest_hex,
        previous_event_hash,
        created_at_ms
    );
    h.update(line.as_bytes());
    hex::encode(h.finalize())
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DerivedAuditVerdict {
    Unknown,
    Valid,
    Invalid,
    Blocked,
}

impl DerivedAuditVerdict {
    pub fn as_str(&self) -> &'static str {
        match self {
            DerivedAuditVerdict::Unknown => "UNKNOWN",
            DerivedAuditVerdict::Valid => "VALID",
            DerivedAuditVerdict::Invalid => "INVALID",
            DerivedAuditVerdict::Blocked => "BLOCKED",
        }
    }
}

/// Deterministic derivation from `policy_eval` outcomes plus `completed` presence.
/// Rules: any `block` => BLOCKED; else any `warn` => INVALID; else if `completed` and every
/// `policy_eval` outcome is `allow` (or there are zero policy_eval events) => VALID; no completed
/// or non-allow/non-warn/non-block policy outcome => UNKNOWN.
pub fn derive_audit_verdict_from_events(events: &[Value]) -> DerivedAuditVerdict {
    let mut has_completed = false;
    let mut saw_policy = false;
    let mut any_block = false;
    let mut any_warn = false;
    let mut all_policy_allow = true;
    for e in events {
        let et = e.get("event_type").and_then(|x| x.as_str()).unwrap_or("");
        if et == "completed" {
            has_completed = true;
            continue;
        }
        if et != "policy_eval" {
            continue;
        }
        saw_policy = true;
        let payload = e.get("payload").cloned().unwrap_or(json!({}));
        let out = payload
            .get("outcome")
            .and_then(|x| x.as_str())
            .unwrap_or("");
        match out {
            "block" => {
                any_block = true;
                all_policy_allow = false;
            }
            "warn" => {
                any_warn = true;
                all_policy_allow = false;
            }
            "allow" => {}
            _ => {
                all_policy_allow = false;
            }
        }
    }
    if !has_completed {
        return DerivedAuditVerdict::Unknown;
    }
    if any_block {
        return DerivedAuditVerdict::Blocked;
    }
    if any_warn {
        return DerivedAuditVerdict::Invalid;
    }
    if saw_policy && !all_policy_allow {
        return DerivedAuditVerdict::Unknown;
    }
    DerivedAuditVerdict::Valid
}

fn parse_producer_verdict(events: &[Value]) -> Option<String> {
    for e in events.iter().rev() {
        if e.get("event_type").and_then(|x| x.as_str()) != Some("completed") {
            continue;
        }
        let p = e.get("payload").cloned().unwrap_or(json!({}));
        return p
            .get("final_audit_verdict")
            .and_then(|x| x.as_str())
            .map(|s| s.to_string());
    }
    None
}

pub fn verdict_detail(events: &[Value]) -> Value {
    let derived = derive_audit_verdict_from_events(events);
    let producer = parse_producer_verdict(events);
    let consistent = match (&producer, &derived) {
        (Some(p), d) => p == d.as_str(),
        (None, DerivedAuditVerdict::Unknown) => true,
        (None, _) => false,
    };
    json!({
        "derived_audit_verdict": derived.as_str(),
        "producer_final_audit_verdict": producer,
        "verdict_consistent": consistent,
    })
}

#[derive(Debug, Clone, Default)]
pub struct DelegationDagReport {
    pub agent_nodes: Vec<String>,
    pub delegation_edges: Vec<Value>,
    pub delegation_chain_valid: bool,
    pub delegation_chain_depth: i64,
    pub delegation_cycle_detected: bool,
    pub missing_parent_or_root: bool,
    pub duplicate_edge_count: i64,
    pub delegation_issues: Vec<String>,
}

impl DelegationDagReport {
    pub fn to_json(&self) -> Value {
        json!({
            "agent_nodes": self.agent_nodes,
            "delegation_edges": self.delegation_edges,
            "delegation_chain_valid": self.delegation_chain_valid,
            "delegation_chain_depth": self.delegation_chain_depth,
            "delegation_cycle_detected": self.delegation_cycle_detected,
            "missing_parent_or_root": self.missing_parent_or_root,
            "duplicate_edge_count": self.duplicate_edge_count,
            "delegation_issues": self.delegation_issues,
        })
    }
}

pub fn analyze_delegation_dag(root_agent_id: &str, delegations: &[Value]) -> DelegationDagReport {
    let mut issues: Vec<String> = Vec::new();
    let mut edge_keys: HashSet<(String, String)> = HashSet::new();
    let mut dup = 0i64;
    let mut adj: HashMap<String, Vec<String>> = HashMap::new();
    let mut all_nodes: HashSet<String> = HashSet::new();
    all_nodes.insert(root_agent_id.to_string());
    let mut edges_out: Vec<Value> = Vec::new();
    for d in delegations {
        let p = d
            .get("parent_agent_id")
            .and_then(|x| x.as_str())
            .unwrap_or("")
            .to_string();
        let c = d
            .get("child_agent_id")
            .and_then(|x| x.as_str())
            .unwrap_or("")
            .to_string();
        if p.is_empty() || c.is_empty() {
            continue;
        }
        edges_out.push(json!({
            "parent_agent_id": p,
            "child_agent_id": c,
            "child_role": d.get("child_role"),
        }));
        let key = (p.clone(), c.clone());
        if !edge_keys.insert(key) {
            dup += 1;
            issues.push(format!("duplicate_edge:{p}->{c}"));
        }
        adj.entry(p.clone()).or_default().push(c.clone());
        all_nodes.insert(p);
        all_nodes.insert(c);
    }
    let children: HashSet<String> = delegations
        .iter()
        .filter_map(|d| {
            d.get("child_agent_id")
                .and_then(|x| x.as_str())
                .map(String::from)
        })
        .collect();
    let mut missing = false;
    for d in delegations {
        let p = d
            .get("parent_agent_id")
            .and_then(|x| x.as_str())
            .unwrap_or("");
        let c = d
            .get("child_agent_id")
            .and_then(|x| x.as_str())
            .unwrap_or("");
        if p.is_empty() || c.is_empty() {
            continue;
        }
        if p != root_agent_id && !children.contains(p) {
            missing = true;
            issues.push(format!("missing_parent_chain:{p}->{c}"));
        }
    }
    fn dfs_cycle(
        u: &str,
        adj: &HashMap<String, Vec<String>>,
        visiting: &mut HashSet<String>,
    ) -> bool {
        if visiting.contains(u) {
            return true;
        }
        visiting.insert(u.to_string());
        for v in adj.get(u).map(Vec::as_slice).unwrap_or(&[]) {
            if dfs_cycle(v, adj, visiting) {
                return true;
            }
        }
        visiting.remove(u);
        false
    }
    let mut visiting = HashSet::new();
    let cycle = dfs_cycle(root_agent_id, &adj, &mut visiting);
    if cycle {
        issues.push("delegation_cycle".into());
    }
    fn max_depth_from(
        u: &str,
        adj: &HashMap<String, Vec<String>>,
        path: &mut HashSet<String>,
    ) -> i64 {
        if path.contains(u) {
            return 0;
        }
        path.insert(u.to_string());
        let mut best = 0i64;
        for c in adj.get(u).map(Vec::as_slice).unwrap_or(&[]) {
            best = best.max(1 + max_depth_from(c, adj, path));
        }
        path.remove(u);
        best
    }
    let max_depth = max_depth_from(root_agent_id, &adj, &mut HashSet::new());
    let valid = !cycle && !missing && dup == 0;
    let mut nodes: Vec<String> = all_nodes.into_iter().collect();
    nodes.sort();
    DelegationDagReport {
        agent_nodes: nodes,
        delegation_edges: edges_out,
        delegation_chain_valid: valid,
        delegation_chain_depth: max_depth,
        delegation_cycle_detected: cycle,
        missing_parent_or_root: missing,
        duplicate_edge_count: dup,
        delegation_issues: issues,
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IntegrityStatus {
    Ok,
    IncompleteMetadata,
    SeqGap,
    PayloadDigestMismatch,
    PrevHashMismatch,
    BrokenChain,
}

impl IntegrityStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            IntegrityStatus::Ok => "ok",
            IntegrityStatus::IncompleteMetadata => "incomplete_metadata",
            IntegrityStatus::SeqGap => "seq_gap",
            IntegrityStatus::PayloadDigestMismatch => "payload_digest_mismatch",
            IntegrityStatus::PrevHashMismatch => "prev_hash_mismatch",
            IntegrityStatus::BrokenChain => "broken_chain",
        }
    }
}

pub fn verify_event_chain_rows(
    ledger_tenant_id: &str,
    run_id: &str,
    rows: &[(
        i64,
        String,
        String,
        String,
        String,
        String,
        DateTime<Utc>,
        Value,
    )],
) -> (IntegrityStatus, Value) {
    if rows.is_empty() {
        return (
            IntegrityStatus::Ok,
            json!({ "integrity_status": "ok", "detail": "empty" }),
        );
    }
    let mut expected_seq = 1i64;
    let mut prev_expected = GENESIS_PREV.to_string();
    for (seq, etype, digest, prev_stored, hash_stored, algo, created_at, payload) in rows {
        if *seq != expected_seq {
            return (
                IntegrityStatus::SeqGap,
                json!({
                    "integrity_status": IntegrityStatus::SeqGap.as_str(),
                    "expected_seq": expected_seq,
                    "observed_seq": seq,
                }),
            );
        }
        expected_seq += 1;
        if algo == DIGEST_CANONICAL {
            let recomputed = canonical_payload_digest_hex(payload);
            if &recomputed != digest {
                return (
                    IntegrityStatus::PayloadDigestMismatch,
                    json!({
                        "integrity_status": IntegrityStatus::PayloadDigestMismatch.as_str(),
                        "event_seq": seq,
                    }),
                );
            }
        }
        if prev_stored != &prev_expected {
            return (
                IntegrityStatus::PrevHashMismatch,
                json!({
                    "integrity_status": IntegrityStatus::PrevHashMismatch.as_str(),
                    "event_seq": seq,
                }),
            );
        }
        let ms = created_at.timestamp_millis();
        let recomputed_hash = event_hash_hex(
            ledger_tenant_id,
            run_id,
            *seq,
            etype,
            digest,
            &prev_expected,
            ms,
        );
        if &recomputed_hash != hash_stored {
            return (
                IntegrityStatus::BrokenChain,
                json!({
                    "integrity_status": IntegrityStatus::BrokenChain.as_str(),
                    "event_seq": seq,
                }),
            );
        }
        prev_expected = hash_stored.clone();
    }
    (
        IntegrityStatus::Ok,
        json!({
            "integrity_status": "ok",
            "event_count": rows.len(),
            "terminal_event_hash": prev_expected,
        }),
    )
}

pub fn verify_integrity_from_api_events(
    ledger_tenant_id: &str,
    run_id: &str,
    events: &[Value],
) -> (IntegrityStatus, Value) {
    let mut rows: Vec<(
        i64,
        String,
        String,
        String,
        String,
        String,
        DateTime<Utc>,
        Value,
    )> = Vec::new();
    for e in events {
        let seq = e.get("event_seq").and_then(|v| v.as_i64()).unwrap_or(0);
        let et = e
            .get("event_type")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let payload = e.get("payload").cloned().unwrap_or(json!({}));
        let digest = e
            .get("canonical_payload_digest")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let prev = e
            .get("previous_event_hash")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let eh = e
            .get("event_hash")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let algo = e
            .get("payload_digest_algorithm")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let ca = e.get("created_at").and_then(|v| v.as_str()).unwrap_or("");
        let parsed = chrono::DateTime::parse_from_rfc3339(ca)
            .map(|x| x.with_timezone(&Utc))
            .unwrap_or_else(|_| Utc::now());
        if seq == 0 || digest.is_empty() || eh.is_empty() || algo.is_empty() {
            return (
                IntegrityStatus::IncompleteMetadata,
                json!({
                    "integrity_status": IntegrityStatus::IncompleteMetadata.as_str(),
                    "hint": "missing_hash_chain_columns",
                }),
            );
        }
        rows.push((seq, et, digest, prev, eh, algo, parsed, payload));
    }
    rows.sort_by_key(|r| r.0);
    verify_event_chain_rows(ledger_tenant_id, run_id, &rows)
}

pub fn merge_completed_for_verdict(events: &[Value], completed_payload: &Value) -> Vec<Value> {
    let mut v: Vec<Value> = events
        .iter()
        .filter(|e| e.get("event_type").and_then(|x| x.as_str()) != Some("completed"))
        .cloned()
        .collect();
    v.push(json!({
        "event_type": "completed",
        "payload": completed_payload,
    }));
    v
}

pub fn explainability_summary_from_events(events: &[Value]) -> Value {
    let mut last_policy: Option<Value> = None;
    let mut completed_ex: Option<Value> = None;
    let mut last_executive: Option<Value> = None;
    let mut appeal_open = 0i64;
    let mut incident_open = 0i64;
    for e in events {
        match e.get("event_type").and_then(|x| x.as_str()) {
            Some("policy_eval") => {
                last_policy = Some(e.get("payload").cloned().unwrap_or(json!({})));
            }
            Some("completed") => {
                completed_ex = Some(e.get("payload").cloned().unwrap_or(json!({})));
            }
            Some("executive_brief") => {
                last_executive = Some(e.get("payload").cloned().unwrap_or(json!({})));
            }
            Some("appeal") => {
                let st = e
                    .get("payload")
                    .and_then(|p| p.get("status"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                if matches!(st, "submitted" | "under_review") {
                    appeal_open += 1;
                }
            }
            Some("incident") => {
                let st = e
                    .get("payload")
                    .and_then(|p| p.get("status"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                if matches!(st, "open" | "mitigating") {
                    incident_open += 1;
                }
            }
            _ => {}
        }
    }
    json!({
        "last_policy_eval": last_policy,
        "completed": completed_ex,
        "last_executive_brief": last_executive,
        "open_appeal_signals": appeal_open,
        "open_incident_signals": incident_open,
    })
}

pub fn human_workflow_export(last_human: &Value, verdict: &Value) -> Value {
    let derived = verdict
        .get("derived_audit_verdict")
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN");
    let producer = verdict
        .get("producer_final_audit_verdict")
        .and_then(|v| v.as_str());
    let override_state = last_human
        .get("override_state")
        .and_then(|v| v.as_str())
        .unwrap_or("none");
    let override_conflicts =
        override_state == "applied" && producer.map(|p| p != derived).unwrap_or(false);
    json!({
        "approval_state": last_human.get("approval_state").cloned().unwrap_or(json!("unknown")),
        "override_state": last_human.get("override_state").cloned().unwrap_or(json!("none")),
        "approver_principal": last_human.get("approver_principal"),
        "approver_identity_hash": last_human.get("approver_identity_hash"),
        "approval_reason": last_human.get("approval_reason"),
        "approval_timestamp": last_human.get("approval_timestamp"),
        "override_conflicts_derived_verdict": override_conflicts,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_digest_stable_key_order() {
        let a = json!({"z": 1, "a": 2});
        let b = json!({"a": 2, "z": 1});
        assert_eq!(
            canonical_payload_digest_hex(&a),
            canonical_payload_digest_hex(&b)
        );
    }

    #[test]
    fn derive_verdict_rules() {
        let ev = vec![
            json!({"event_type": "trace_started", "payload": {}}),
            json!({"event_type": "policy_eval", "payload": {"outcome": "allow"}}),
            json!({"event_type": "completed", "payload": {"final_audit_verdict": "VALID"}}),
        ];
        assert_eq!(
            derive_audit_verdict_from_events(&ev),
            DerivedAuditVerdict::Valid
        );

        let ev2 = vec![
            json!({"event_type": "policy_eval", "payload": {"outcome": "warn"}}),
            json!({"event_type": "completed", "payload": {"final_audit_verdict": "INVALID"}}),
        ];
        assert_eq!(
            derive_audit_verdict_from_events(&ev2),
            DerivedAuditVerdict::Invalid
        );

        let ev3 = vec![
            json!({"event_type": "policy_eval", "payload": {"outcome": "block"}}),
            json!({"event_type": "completed", "payload": {"final_audit_verdict": "BLOCKED"}}),
        ];
        assert_eq!(
            derive_audit_verdict_from_events(&ev3),
            DerivedAuditVerdict::Blocked
        );

        let ev4 =
            vec![json!({"event_type": "completed", "payload": {"final_audit_verdict": "VALID"}})];
        assert_eq!(
            derive_audit_verdict_from_events(&ev4),
            DerivedAuditVerdict::Valid
        );

        let ev5 = vec![json!({"event_type": "policy_eval", "payload": {"outcome": "allow"}})];
        assert_eq!(
            derive_audit_verdict_from_events(&ev5),
            DerivedAuditVerdict::Unknown
        );
    }

    #[test]
    fn delegation_cycle() {
        let rep = analyze_delegation_dag(
            "lead",
            &[
                json!({"parent_agent_id": "lead", "child_agent_id": "a", "child_role": "x"}),
                json!({"parent_agent_id": "a", "child_agent_id": "b", "child_role": "x"}),
                json!({"parent_agent_id": "b", "child_agent_id": "a", "child_role": "x"}),
            ],
        );
        assert!(rep.delegation_cycle_detected);
        assert!(!rep.delegation_chain_valid);
    }

    #[test]
    fn hash_chain_roundtrip() {
        let ledger = "t1";
        let run = "r1";
        let payload = json!({"a": 1});
        let d = canonical_payload_digest_hex(&payload);
        let ts = Utc::now();
        let ms = ts.timestamp_millis();
        let h = event_hash_hex(ledger, run, 1, "trace_started", &d, GENESIS_PREV, ms);
        let rows = vec![(
            1i64,
            "trace_started".to_string(),
            d,
            GENESIS_PREV.to_string(),
            h,
            DIGEST_CANONICAL.to_string(),
            ts,
            payload,
        )];
        let (st, _) = verify_event_chain_rows(ledger, run, &rows);
        assert_eq!(st, IntegrityStatus::Ok);
    }
}
