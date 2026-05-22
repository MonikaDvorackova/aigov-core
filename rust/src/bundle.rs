use crate::schema::EvidenceEvent;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::cmp::Ordering;
use std::collections::BTreeMap;
use std::collections::HashSet;

/// Same ordering/de-duplication as historical `canonicalize_events` in `govai_api` /
/// `/bundle-hash`, so digest and bundle hashing apply to identical event sequences.
pub fn canonicalize_evidence_events(mut events: Vec<EvidenceEvent>) -> Vec<EvidenceEvent> {
    let mut seen: HashSet<String> = HashSet::new();
    events.sort_by(|a, b| a.ts_utc.cmp(&b.ts_utc));
    let mut out_rev: Vec<EvidenceEvent> = Vec::with_capacity(events.len());
    for e in events.into_iter().rev() {
        if seen.insert(e.event_id.clone()) {
            out_rev.push(e);
        }
    }
    out_rev.reverse();

    out_rev.sort_by(|a, b| {
        a.ts_utc
            .cmp(&b.ts_utc)
            .then_with(|| a.event_type.cmp(&b.event_type))
            .then_with(|| a.event_id.cmp(&b.event_id))
    });

    out_rev
}

/// Cross-environment ledger digest over evidence events only (`run_id`, ordered events with
/// `environment` stripped). Stable across `policy_version`, host path, or chain linkage.
///
/// Contracts with `events_content_sha256` on `/bundle-hash` / export metadata.
pub fn portable_evidence_digest_v1(run_id: &str, events: &[EvidenceEvent]) -> String {
    let run_id_trim = run_id.trim();
    let seq = canonicalize_evidence_events(events.to_vec());

    let ev_values: Vec<serde_json::Value> = seq
        .into_iter()
        .map(|e| {
            let stripped = EvidenceEvent {
                environment: None,
                ..e
            };
            sort_json_value(serde_json::to_value(stripped).expect("EvidenceEvent serde"))
        })
        .collect();

    let v = serde_json::json!({
        "events": ev_values,
        "run_id": run_id_trim,
        "schema": "aigov.evidence_digest.v1"
    });

    let bytes = canonical_json_bytes(&v);
    let mut h = Sha256::new();
    h.update(bytes);
    hex::encode(h.finalize())
}

fn canonical_json_bytes<T: Serialize>(value: &T) -> Vec<u8> {
    // serde_json keeps insertion order, but we need canonical ordering
    // Convert to Value, sort keys recursively, then serialize
    let v = serde_json::to_value(value).expect("to_value");
    let sorted = sort_json_value(v);
    serde_json::to_vec(&sorted).expect("to_vec")
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

pub fn collect_events_for_run(log_path: &str, run_id: &str) -> Result<Vec<EvidenceEvent>, String> {
    let mut out: Vec<EvidenceEvent> = Vec::new();
    let (records, _diag) = crate::audit_store::scan_ledger_records(log_path)?;
    for rec in records {
        // Prefer the stored JSON to avoid re-serialization differences.
        let ev: EvidenceEvent = serde_json::from_str(&rec.event_json).map_err(|e| e.to_string())?;
        if ev.run_id == run_id {
            out.push(ev);
        }
    }

    // Stable ordering for exports and hashing
    out.sort_by(stable_event_order);

    Ok(out)
}

pub fn find_model_artifact_path(events: &[EvidenceEvent]) -> Option<String> {
    for e in events.iter().rev() {
        if e.event_type == "model_promoted" {
            if let Some(ap) = e.payload.get("artifact_path").and_then(|v| v.as_str()) {
                let ap = ap.trim();
                if !ap.is_empty() {
                    return Some(ap.to_string());
                }
            }
        }
    }
    None
}

fn payload_get_str(payload: &serde_json::Value, key: &str) -> Option<String> {
    payload
        .get(key)
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
}

fn payload_get_num(payload: &serde_json::Value, key: &str) -> Option<f64> {
    payload.get(key).and_then(|v| v.as_f64())
}

fn find_last_payload_str_for_event_types(
    events: &[EvidenceEvent],
    event_types: &[&str],
    key: &str,
) -> Option<String> {
    events
        .iter()
        .rev()
        .find(|e| event_types.contains(&e.event_type.as_str()))
        .and_then(|e| payload_get_str(&e.payload, key))
}

fn extract_canonical_identifiers(events: &[EvidenceEvent]) -> serde_json::Value {
    let ai_system_id = find_last_payload_str_for_event_types(
        events,
        &[
            "data_registered",
            "model_trained",
            "evaluation_reported",
            "risk_recorded",
            "risk_mitigated",
            "risk_reviewed",
            "human_approved",
            "model_promoted",
        ],
        "ai_system_id",
    );
    let dataset_id = find_last_payload_str_for_event_types(
        events,
        &[
            "data_registered",
            "model_trained",
            "evaluation_reported",
            "risk_recorded",
            "risk_mitigated",
            "risk_reviewed",
            "human_approved",
            "model_promoted",
        ],
        "dataset_id",
    );
    let model_version_id = find_last_payload_str_for_event_types(
        events,
        &[
            "model_trained",
            "evaluation_reported",
            "risk_recorded",
            "risk_mitigated",
            "risk_reviewed",
            "human_approved",
            "model_promoted",
        ],
        "model_version_id",
    );

    // Match projection: only risk lifecycle events contribute to the authoritative risk_id set.
    let mut risk_ids: BTreeMap<String, ()> = BTreeMap::new();
    for e in events.iter() {
        if e.event_type != "risk_recorded"
            && e.event_type != "risk_mitigated"
            && e.event_type != "risk_reviewed"
        {
            continue;
        }
        if let Some(rid) = payload_get_str(&e.payload, "risk_id") {
            risk_ids.insert(rid, ());
        }
    }
    let risk_ids: Vec<String> = risk_ids.keys().cloned().collect();
    let primary_risk_id = risk_ids.first().cloned();

    serde_json::json!({
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_version_id": model_version_id,
        "primary_risk_id": primary_risk_id,
        "risk_ids": risk_ids
    })
}

fn extract_dataset_governance(events: &[EvidenceEvent]) -> Option<serde_json::Value> {
    for e in events.iter().rev() {
        if e.event_type != "data_registered" {
            continue;
        }

        let p = &e.payload;
        let ai_system_id = payload_get_str(p, "ai_system_id")?;
        let dataset_id = payload_get_str(p, "dataset_id")?;
        let dataset = payload_get_str(p, "dataset")?;
        let dataset_version = payload_get_str(p, "dataset_version")?;
        let dataset_fingerprint = payload_get_str(p, "dataset_fingerprint")?;
        let dataset_governance_id = payload_get_str(p, "dataset_governance_id")?;
        let dataset_governance_commitment = payload_get_str(p, "dataset_governance_commitment")?;

        let source = payload_get_str(p, "source")?;
        let intended_use = payload_get_str(p, "intended_use")?;
        let limitations = payload_get_str(p, "limitations")?;
        let quality_summary = payload_get_str(p, "quality_summary")?;
        let governance_status = payload_get_str(p, "governance_status")?;

        return Some(serde_json::json!({
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "dataset": dataset,
            "dataset_version": dataset_version,
            "dataset_fingerprint": dataset_fingerprint,
            "dataset_governance_id": dataset_governance_id,
            "dataset_governance_commitment": dataset_governance_commitment,
            "source": source,
            "intended_use": intended_use,
            "limitations": limitations,
            "quality_summary": quality_summary,
            "governance_status": governance_status
        }));
    }

    None
}

fn extract_evaluation(events: &[EvidenceEvent]) -> Option<serde_json::Value> {
    for e in events.iter().rev() {
        if e.event_type != "evaluation_reported" {
            continue;
        }
        let p = &e.payload;
        let ai_system_id = payload_get_str(p, "ai_system_id")?;
        let dataset_id = payload_get_str(p, "dataset_id")?;
        let model_version_id = payload_get_str(p, "model_version_id")?;
        let metric = payload_get_str(p, "metric")?;
        let value = p.get("value")?.as_f64()?;
        let threshold = p.get("threshold")?.as_f64()?;
        let passed = p.get("passed")?.as_bool()?;

        return Some(serde_json::json!({
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
            "metric": metric,
            "value": value,
            "threshold": threshold,
            "passed": passed,
            "event_id": e.event_id,
            "ts_utc": e.ts_utc
        }));
    }
    None
}

fn extract_human_approval(events: &[EvidenceEvent]) -> Option<serde_json::Value> {
    for e in events.iter().rev() {
        if e.event_type != "human_approved" {
            continue;
        }

        let scope = payload_get_str(&e.payload, "scope").unwrap_or_default();
        if scope != "model_promoted" {
            continue;
        }

        let decision = payload_get_str(&e.payload, "decision").unwrap_or_default();
        let approver = payload_get_str(&e.payload, "approver")?;
        let justification = payload_get_str(&e.payload, "justification")?;
        let assessment_id = payload_get_str(&e.payload, "assessment_id")?;
        let risk_id = payload_get_str(&e.payload, "risk_id")?;
        let dataset_governance_commitment =
            payload_get_str(&e.payload, "dataset_governance_commitment")?;
        let ai_system_id = payload_get_str(&e.payload, "ai_system_id")?;
        let dataset_id = payload_get_str(&e.payload, "dataset_id")?;
        let model_version_id = payload_get_str(&e.payload, "model_version_id")?;

        return Some(serde_json::json!({
            "approval_event_id": e.event_id,
            "ts_utc": e.ts_utc,
            "decision": decision,
            "approver": approver,
            "justification": justification,
            "assessment_id": assessment_id,
            "risk_id": risk_id,
            "dataset_governance_commitment": dataset_governance_commitment,
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id
        }));
    }
    None
}

fn extract_promotion_decision(events: &[EvidenceEvent]) -> Option<serde_json::Value> {
    for e in events.iter().rev() {
        if e.event_type != "model_promoted" {
            continue;
        }

        let artifact_path = payload_get_str(&e.payload, "artifact_path")?;
        let promotion_reason = payload_get_str(&e.payload, "promotion_reason")?;
        let approved_human_event_id = payload_get_str(&e.payload, "approved_human_event_id")?;
        let assessment_id = payload_get_str(&e.payload, "assessment_id")?;
        let risk_id = payload_get_str(&e.payload, "risk_id")?;
        let dataset_governance_commitment =
            payload_get_str(&e.payload, "dataset_governance_commitment")?;
        let ai_system_id = payload_get_str(&e.payload, "ai_system_id")?;
        let dataset_id = payload_get_str(&e.payload, "dataset_id")?;
        let model_version_id = payload_get_str(&e.payload, "model_version_id")?;

        let artifact_sha256 = payload_get_str(&e.payload, "artifact_sha256");

        return Some(serde_json::json!({
            "promotion_event_id": e.event_id,
            "ts_utc": e.ts_utc,
            "artifact_path": artifact_path,
            "artifact_sha256": artifact_sha256,
            "promotion_reason": promotion_reason,
            "approved_human_event_id": approved_human_event_id,
            "assessment_id": assessment_id,
            "risk_id": risk_id,
            "dataset_governance_commitment": dataset_governance_commitment,
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id
        }));
    }
    None
}

fn extract_model_version(events: &[EvidenceEvent]) -> Option<serde_json::Value> {
    let trained = events
        .iter()
        .rev()
        .find(|e| e.event_type == "model_trained");
    let promoted = events
        .iter()
        .rev()
        .find(|e| e.event_type == "model_promoted");

    let trained = match trained {
        Some(t) => t,
        None => return None,
    };

    let p = &trained.payload;
    let model_version_id = payload_get_str(p, "model_version_id")?;
    let model_type = payload_get_str(p, "model_type")?;
    let artifact_sha256 = payload_get_str(p, "artifact_sha256");
    let ai_system_id = payload_get_str(p, "ai_system_id")?;
    let dataset_id = payload_get_str(p, "dataset_id")?;

    // Include both training params and (if promotion exists) final promotion linkage.
    let training_params = p
        .get("training_params")
        .cloned()
        .or_else(|| p.get("params").cloned());

    let mut out = serde_json::json!({
        "ai_system_id": ai_system_id,
        "dataset_id": dataset_id,
        "model_version_id": model_version_id,
        "model_type": model_type,
        "trained_ts_utc": trained.ts_utc,
        "artifact_sha256": artifact_sha256,
        "training_params": training_params,
    });

    if let Some(promoted) = promoted {
        let pp = &promoted.payload;
        let artifact_path = payload_get_str(pp, "artifact_path");
        out.as_object_mut().unwrap().insert(
            "artifact_path".to_string(),
            serde_json::json!(artifact_path),
        );

        let promotion_reason = payload_get_str(pp, "promotion_reason");
        out.as_object_mut().unwrap().insert(
            "promotion_reason".to_string(),
            serde_json::json!(promotion_reason),
        );
    }

    Some(out)
}

fn extract_risk_register(events: &[EvidenceEvent]) -> Option<serde_json::Value> {
    // Gather unique risk_ids from risk lifecycle events.
    let mut risk_ids: BTreeMap<String, ()> = BTreeMap::new();
    for e in events.iter() {
        if e.event_type != "risk_recorded"
            && e.event_type != "risk_mitigated"
            && e.event_type != "risk_reviewed"
        {
            continue;
        }
        if let Some(rid) = payload_get_str(&e.payload, "risk_id") {
            risk_ids.insert(rid, ());
        }
    }

    if risk_ids.is_empty() {
        return None;
    }

    let mut risks: Vec<serde_json::Value> = Vec::new();

    for risk_id in risk_ids.keys() {
        let mut recorded: Option<&EvidenceEvent> = None;
        let mut latest_mitigated: Option<&EvidenceEvent> = None;
        let mut latest_reviewed: Option<&EvidenceEvent> = None;

        let mut history: Vec<serde_json::Value> = Vec::new();

        for e in events.iter() {
            if payload_get_str(&e.payload, "risk_id").as_deref() != Some(risk_id.as_str()) {
                continue;
            }

            if e.event_type == "risk_recorded" {
                recorded = Some(e);
            } else if e.event_type == "risk_mitigated" {
                latest_mitigated = Some(e);
            } else if e.event_type == "risk_reviewed" {
                latest_reviewed = Some(e);
            }

            if e.event_type.starts_with("risk_") {
                history.push(serde_json::json!({
                    "event_type": e.event_type,
                    "event_id": e.event_id,
                    "ts_utc": e.ts_utc
                }));
            }
        }

        let recorded = recorded.or(latest_mitigated).or(latest_reviewed)?;
        let rp = &recorded.payload;
        let assessment_id = payload_get_str(rp, "assessment_id");
        let dataset_commitment = payload_get_str(rp, "dataset_governance_commitment");
        let ai_system_id = payload_get_str(rp, "ai_system_id");
        let dataset_id = payload_get_str(rp, "dataset_id");
        let model_version_id = payload_get_str(rp, "model_version_id");
        let risk_class = payload_get_str(rp, "risk_class");

        let severity = payload_get_num(rp, "severity");
        let likelihood = payload_get_num(rp, "likelihood");

        // Mitigation and status come from the latest mitigation event, if present; otherwise from the recorded event.
        let mp = &latest_mitigated.unwrap_or(recorded).payload;
        let status = payload_get_str(mp, "status");
        let mitigation = payload_get_str(mp, "mitigation");
        let owner = payload_get_str(mp, "owner");

        let review = if let Some(r) = latest_reviewed {
            let pp = &r.payload;
            serde_json::json!({
                "risk_review_event_id": r.event_id,
                "ts_utc": r.ts_utc,
                "decision": payload_get_str(pp, "decision"),
                "reviewer": payload_get_str(pp, "reviewer"),
                "justification": payload_get_str(pp, "justification"),
            })
        } else {
            serde_json::Value::Null
        };

        risks.push(serde_json::json!({
            "risk_id": risk_id,
            "assessment_id": assessment_id,
            "risk_class": risk_class,
            "severity": severity,
            "likelihood": likelihood,
            "dataset_governance_commitment": dataset_commitment,
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
            "status": status,
            "mitigation": mitigation,
            "owner": owner,
            "latest_review": review,
            "history": history
        }));
    }

    Some(serde_json::json!({ "risks": risks }))
}

fn stable_event_order(a: &EvidenceEvent, b: &EvidenceEvent) -> Ordering {
    // primary timestamp
    let t = a.ts_utc.cmp(&b.ts_utc);
    if t != Ordering::Equal {
        return t;
    }

    // secondary event_type
    let et = a.event_type.cmp(&b.event_type);
    if et != Ordering::Equal {
        return et;
    }

    // tertiary event_id
    a.event_id.cmp(&b.event_id)
}

fn canonicalize_json(v: &mut serde_json::Value) {
    match v {
        serde_json::Value::Object(map) => {
            let mut keys: Vec<String> = map.keys().cloned().collect();
            keys.sort();

            let mut new_map = serde_json::Map::with_capacity(map.len());
            for k in keys {
                let mut val = map.remove(&k).unwrap();
                canonicalize_json(&mut val);
                new_map.insert(k, val);
            }
            *map = new_map;
        }
        serde_json::Value::Array(arr) => {
            // Keep array order as is, event order is handled separately
            for x in arr.iter_mut() {
                canonicalize_json(x);
            }
        }
        _ => {}
    }
}

fn canonical_bundle_value(
    run_id: &str,
    policy_version: &str,
    log_path: &str,
    model_artifact_path: Option<&str>,
    events: &[EvidenceEvent],
) -> serde_json::Value {
    let dataset_governance = extract_dataset_governance(events);
    let evaluation = extract_evaluation(events);
    let risk_register = extract_risk_register(events);
    let human_approval = extract_human_approval(events);
    let promotion = extract_promotion_decision(events);
    let model_version = extract_model_version(events);
    let identifiers = extract_canonical_identifiers(events);

    let mut v = serde_json::json!({
        "ok": true,
        "run_id": run_id,
        "policy_version": policy_version,
        "schema_version": "aigov.bundle.v1",
        "log_path": log_path,
        "model_artifact_path": model_artifact_path,
        "identifiers": identifiers,
        "dataset_governance": dataset_governance,
        "model_version": model_version,
        "evaluation": evaluation,
        "risk_register": risk_register,
        "human_approval": human_approval,
        "promotion": promotion,
        "events": events
    });

    canonicalize_json(&mut v);
    v
}

pub fn bundle_document_value(
    run_id: &str,
    policy_version: &str,
    log_path: &str,
    events: &[EvidenceEvent],
) -> serde_json::Value {
    let artifact_path = find_model_artifact_path(events);
    canonical_bundle_value(
        run_id,
        policy_version,
        log_path,
        artifact_path.as_deref(),
        events,
    )
}

pub fn bundle_sha256(
    run_id: &str,
    policy_version: &str,
    log_path: &str,
    model_artifact_path: Option<&str>,
    events: &[EvidenceEvent],
) -> String {
    let v = canonical_bundle_value(
        run_id,
        policy_version,
        log_path,
        model_artifact_path,
        events,
    );

    // Serialize with canonical key ordering
    let bytes = canonical_json_bytes(&v);

    let mut h = Sha256::new();
    h.update(bytes);
    hex::encode(h.finalize())
}

#[cfg(test)]
mod portable_digest_tests {
    use super::*;
    use crate::schema::EvidenceEvent;

    fn ev_sample(
        id: &str,
        et: &str,
        ts: &str,
        rid: &str,
        environment: Option<&str>,
        payload: serde_json::Value,
    ) -> EvidenceEvent {
        EvidenceEvent {
            event_id: id.to_string(),
            event_type: et.to_string(),
            ts_utc: ts.to_string(),
            actor: "actor_x".to_string(),
            system: "sys_y".to_string(),
            run_id: rid.to_string(),
            environment: environment.map(|s| s.to_string()),
            payload,
        }
    }

    #[test]
    fn portable_digest_ignores_environment_stamp() {
        let rid = "rid-env-invariant";
        let a = vec![ev_sample(
            "e1",
            "ai_discovery_reported",
            "2020-01-01T01:02:03Z",
            rid,
            Some("dev"),
            serde_json::json!({"openai": false}),
        )];
        let b = vec![ev_sample(
            "e1",
            "ai_discovery_reported",
            "2020-01-01T01:02:03Z",
            rid,
            None,
            serde_json::json!({"openai": false}),
        )];
        assert_eq!(
            portable_evidence_digest_v1(rid, &a),
            portable_evidence_digest_v1(rid, &b)
        );
    }

    #[test]
    fn portable_digest_deterministic_repeated_calls() {
        let rid = "rid-stable";
        let events = vec![ev_sample(
            "evt-a",
            "ai_discovery_reported",
            "2021-06-07T08:09:10Z",
            rid,
            Some("staging"),
            serde_json::json!({"openai": false, "transformers": true}),
        )];
        let d1 = portable_evidence_digest_v1(rid, &events);
        let d2 = portable_evidence_digest_v1(rid, &events);
        assert_eq!(d1, d2);
        assert!(d1.chars().all(|c| c.is_ascii_hexdigit()));
        assert_eq!(d1.len(), 64);
    }
}
