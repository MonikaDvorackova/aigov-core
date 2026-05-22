//! Stable JSON contract for `GET /api/tenant-console/snapshot` and shared product positioning metadata.
//!
//! Contract is validated in unit tests and `rust/tests/tenant_console_snapshot_http.rs`.

use serde_json::{json, Value};

pub const SNAPSHOT_SCHEMA_VERSION: i32 = 3;

/// Canonical product positioning returned on snapshot, `/api/me`, and selected public metadata routes.
pub fn product_positioning_v1() -> Value {
    json!({
        "version": 1,
        "product": "GovAI is an audit-backed governance backend for AI deployments.",
        "ci_integration": {
            "role": "CI gates and automation are one integration surface against the audit backend; they are not the product definition."
        },
        "product_surfaces": {
            "dashboard_and_tenant_console": "Authenticated UI surfaces over this audit backend; they do not replace ledger verdict semantics."
        },
        "portable_artifacts": {
            "role": "Portable standards, validators, and policy packs are distinct from this hosted or self-hosted audit backend runtime."
        },
        "authoritative_verdict": {
            "http_route": "GET /compliance-summary",
            "description": "Authoritative audit-backed verdict projection over the immutable ledger for a run."
        }
    })
}

/// Validates a successful (HTTP 200) snapshot body after `ok: true` for schema v3.
pub fn validate_tenant_console_snapshot_v1(body: &Value) -> Result<(), String> {
    if body.get("ok").and_then(|v| v.as_bool()) != Some(true) {
        return Err("expected ok=true".into());
    }
    if body.get("snapshot_version").and_then(|v| v.as_i64())
        != Some(i64::from(SNAPSHOT_SCHEMA_VERSION))
    {
        return Err(format!(
            "expected snapshot_version={}",
            SNAPSHOT_SCHEMA_VERSION
        ));
    }
    let required = [
        "product_positioning",
        "generated_at",
        "tenant",
        "audit_backend",
        "runtime_enforcement",
        "ledger_binding",
        "readiness",
        "rbac",
        "product_operations",
        "ai_decision_audit",
        "recent_events",
    ];
    for key in required {
        if body.get(key).is_none() {
            return Err(format!("missing top-level key `{key}`"));
        }
    }
    if !body["product_positioning"].is_object() {
        return Err("product_positioning must be an object".into());
    }
    if body["product_positioning"]["version"].as_i64() != Some(1) {
        return Err("product_positioning.version must be 1".into());
    }
    let prod = body["product_positioning"]["product"]
        .as_str()
        .unwrap_or("");
    if !prod.contains("audit-backed governance backend") {
        return Err(
            "product_positioning.product must contain audit-backed governance backend".into(),
        );
    }
    if body["product_positioning"]["authoritative_verdict"]["http_route"].as_str()
        != Some("GET /compliance-summary")
    {
        return Err("authoritative_verdict.http_route must be GET /compliance-summary".into());
    }
    if !body["generated_at"].is_string() {
        return Err("generated_at must be a string (RFC3339)".into());
    }
    if !body["tenant"].is_object() {
        return Err("tenant must be an object".into());
    }
    if !body["audit_backend"].is_object() {
        return Err("audit_backend must be an object".into());
    }
    if !body["runtime_enforcement"].is_object() {
        return Err("runtime_enforcement must be an object".into());
    }
    if !body["ledger_binding"].is_object() {
        return Err("ledger_binding must be an object".into());
    }
    let lb = &body["ledger_binding"];
    if lb.get("configured").and_then(|v| v.as_bool()).is_none() {
        return Err("ledger_binding.configured must be a bool".into());
    }
    if !body["readiness"].is_object() {
        return Err("readiness must be an object".into());
    }
    if !body["rbac"].is_object() {
        return Err("rbac must be an object".into());
    }
    if !body["product_operations"].is_object() {
        return Err("product_operations must be an object".into());
    }
    let ada = &body["ai_decision_audit"];
    if !ada.is_object() {
        return Err("ai_decision_audit must be an object".into());
    }
    for k in [
        "ledger_scope",
        "data_source",
        "relation_to_compliance_summary",
        "recent_traces",
        "ai_decision_trace_read",
    ] {
        if ada.get(k).is_none() {
            return Err(format!("ai_decision_audit missing `{k}`"));
        }
    }
    if !ada["recent_traces"].is_array() {
        return Err("ai_decision_audit.recent_traces must be an array".into());
    }
    if ada["ai_decision_trace_read"].as_bool().is_none() {
        return Err("ai_decision_audit.ai_decision_trace_read must be a bool".into());
    }
    if ada["data_source"].as_str() == Some("postgres") {
        for (i, row) in ada["recent_traces"].as_array().unwrap().iter().enumerate() {
            if !row.is_object() {
                return Err(format!(
                    "ai_decision_audit.recent_traces[{i}] must be an object"
                ));
            }
            for key in [
                "run_id",
                "trace_integrity_status",
                "derived_audit_verdict",
                "verdict_consistent",
                "delegation_chain_valid",
                "delegation_chain_depth",
            ] {
                if row.get(key).is_none() {
                    return Err(format!(
                        "ai_decision_audit.recent_traces[{i}] missing `{key}` (required when data_source is postgres)"
                    ));
                }
            }
        }
    }
    let rel = ada["relation_to_compliance_summary"].as_str().unwrap_or("");
    if !rel.contains("GET /compliance-summary") {
        return Err("ai_decision_audit.relation_to_compliance_summary must reference GET /compliance-summary".into());
    }
    if !body["recent_events"].is_object() {
        return Err("recent_events must be an object".into());
    }
    let re = &body["recent_events"];
    if !re["governance_identity_audit"].is_array() {
        return Err("recent_events.governance_identity_audit must be an array".into());
    }
    if !re["product_milestones"].is_array() {
        return Err("recent_events.product_milestones must be an array".into());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn product_positioning_semantics() {
        let p = product_positioning_v1();
        assert_eq!(p["version"], json!(1));
        let s = p["product"].as_str().unwrap();
        assert!(s.contains("audit-backed governance backend"), "{s}");
        assert_eq!(
            p["authoritative_verdict"]["http_route"].as_str(),
            Some("GET /compliance-summary")
        );
    }

    #[test]
    fn validator_accepts_minimal_synthetic_snapshot_v3() {
        let v = json!({
            "ok": true,
            "snapshot_version": 3,
            "product_positioning": product_positioning_v1(),
            "generated_at": "2026-01-01T00:00:00.000Z",
            "tenant": { "user_id": "u", "team_id": "t" },
            "audit_backend": {},
            "runtime_enforcement": {},
            "ledger_binding": { "configured": false },
            "readiness": {},
            "rbac": {},
            "product_operations": {},
            "ai_decision_audit": {
                "ledger_scope": "unbound",
                "data_source": "ledger_binding_required",
                "relation_to_compliance_summary": "Verdict from GET /compliance-summary is authoritative.",
                "recent_traces": [],
                "ai_decision_trace_read": true
            },
            "recent_events": {
                "governance_identity_audit": [],
                "product_milestones": []
            }
        });
        validate_tenant_console_snapshot_v1(&v).expect("valid");
    }

    #[test]
    fn validator_rejects_postgres_recent_trace_missing_rollups() {
        let v = json!({
            "ok": true,
            "snapshot_version": 3,
            "product_positioning": product_positioning_v1(),
            "generated_at": "2026-01-01T00:00:00.000Z",
            "tenant": { "user_id": "u", "team_id": "t" },
            "audit_backend": {},
            "runtime_enforcement": {},
            "ledger_binding": { "configured": true, "ledger_tenant_id": "lt" },
            "readiness": {},
            "rbac": {},
            "product_operations": {},
            "ai_decision_audit": {
                "ledger_scope": "bound",
                "data_source": "postgres",
                "relation_to_compliance_summary": "Verdict from GET /compliance-summary is authoritative.",
                "recent_traces": [{ "run_id": "r1" }],
                "ai_decision_trace_read": true
            },
            "recent_events": {
                "governance_identity_audit": [],
                "product_milestones": []
            }
        });
        assert!(validate_tenant_console_snapshot_v1(&v).is_err());
    }
}
