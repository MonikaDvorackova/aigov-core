//! Single-line JSON operational logs (stderr). Never log raw bearer tokens or request bodies.

use chrono::{SecondsFormat, Utc};
use serde_json::{json, Map, Value};

fn emit(obj: Value) {
    eprintln!("{}", obj);
}

fn ts() -> String {
    Utc::now().to_rfc3339_opts(SecondsFormat::Millis, true)
}

fn base(event: &str) -> Map<String, Value> {
    let mut m = Map::new();
    m.insert("ts".into(), json!(ts()));
    m.insert("channel".into(), json!("govai.ops"));
    m.insert("event".into(), json!(event));
    m
}

/// Strip common secret patterns from free-text diagnostic strings (best-effort).
pub fn redact_diagnostic_message(msg: &str) -> String {
    let mut s = msg.to_string();
    const PREFIX: &str = "Bearer ";
    if let Some(i) = s.find(PREFIX) {
        let after = i + PREFIX.len();
        if after <= s.len() {
            let rest = &s[after..];
            let token_len = rest
                .find(|c: char| c.is_whitespace() || c == '"' || c == '\'')
                .unwrap_or_else(|| rest.len().min(32));
            s.replace_range(after..(after + token_len), "<redacted>");
        }
    }
    if s.contains("postgresql://") {
        s = "<redacted database url>".into();
    }
    s
}

pub fn auth_failure_category(code: &str, method: &str, path_metric_key: &str) {
    let mut o = base("auth_failure");
    o.insert("category".into(), json!("api_key_gate"));
    o.insert("code".into(), json!(code));
    o.insert("http_method".into(), json!(method));
    o.insert("route_key".into(), json!(path_metric_key));
    emit(Value::Object(o));
}

pub fn readiness_failure_category(category: &str, detail_redacted: &str) {
    let mut o = base("readiness_failure");
    o.insert("category".into(), json!(category));
    o.insert("detail".into(), json!(redact_diagnostic_message(detail_redacted)));
    emit(Value::Object(o));
}

pub fn evidence_ingest(outcome: &str, http_status: u16, ledger_scope: &str) {
    let mut o = base("evidence_ingest");
    o.insert("outcome".into(), json!(outcome));
    o.insert("http_status".into(), json!(http_status));
    o.insert("ledger_scope".into(), json!(ledger_scope));
    emit(Value::Object(o));
}

pub fn compliance_summary_generated(ledger_scope: &str, run_id_len: usize, verdict: &str) {
    let mut o = base("compliance_summary_generated");
    o.insert("ledger_scope".into(), json!(ledger_scope));
    o.insert("run_id_len".into(), json!(run_id_len));
    o.insert("verdict".into(), json!(verdict));
    emit(Value::Object(o));
}

pub fn ai_trace_event_appended(
    event_type: &str,
    ledger_scope: &str,
    correlation_present: bool,
) {
    let mut o = base("ai_trace_event_appended");
    o.insert("event_type".into(), json!(event_type));
    o.insert("ledger_scope".into(), json!(ledger_scope));
    o.insert("correlation_id_present".into(), json!(correlation_present));
    emit(Value::Object(o));
}

pub fn audit_snapshot_served(ledger_scope: &str, team_id_present: bool) {
    let mut o = base("audit_snapshot_requested");
    o.insert("ledger_scope".into(), json!(ledger_scope));
    o.insert("team_context".into(), json!(if team_id_present {
        "resolved"
    } else {
        "unknown"
    }));
    emit(Value::Object(o));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn redact_strips_bearer_prefix_region() {
        let s = redact_diagnostic_message(r#"token="Bearer abcdefghi" ok"#);
        assert!(!s.contains("abcdef"));
        assert!(s.contains("<redacted>") || s.contains("Bearer"));
    }
}
