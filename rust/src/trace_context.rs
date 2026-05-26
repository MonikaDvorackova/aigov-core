//! W3C Trace Context parsing for optional evidence ↔ external trace linking.
//! No OpenTelemetry SDK dependency — operators may attach IDs to evidence payloads.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExternalTraceContext {
    pub trace_id: String,
    pub span_id: String,
    pub trace_flags: String,
}

/// Parse W3C `traceparent` (version 00): `00-<32hex>-<16hex>-<2hex>`.
pub fn parse_traceparent(value: &str) -> Option<ExternalTraceContext> {
    let s = value.trim();
    let parts: Vec<&str> = s.split('-').collect();
    if parts.len() != 4 || parts[0] != "00" {
        return None;
    }
    let trace_id = parts[1];
    let span_id = parts[2];
    let flags = parts[3];
    if trace_id.len() != 32
        || span_id.len() != 16
        || flags.len() != 2
        || !trace_id.chars().all(|c| c.is_ascii_hexdigit())
        || !span_id.chars().all(|c| c.is_ascii_hexdigit())
        || !flags.chars().all(|c| c.is_ascii_hexdigit())
    {
        return None;
    }
    Some(ExternalTraceContext {
        trace_id: trace_id.to_ascii_lowercase(),
        span_id: span_id.to_ascii_lowercase(),
        trace_flags: flags.to_ascii_lowercase(),
    })
}

/// JSON object suitable for optional `EvidenceEvent.payload["external_trace"]`.
pub fn external_trace_payload(ctx: &ExternalTraceContext) -> serde_json::Value {
    serde_json::json!({
        "trace_id": ctx.trace_id,
        "span_id": ctx.span_id,
        "trace_flags": ctx.trace_flags,
        "propagation": "w3c_traceparent",
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_valid_traceparent() {
        let tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01";
        let ctx = parse_traceparent(tp).expect("parse");
        assert_eq!(ctx.trace_id.len(), 32);
        assert_eq!(ctx.span_id.len(), 16);
        assert_eq!(ctx.trace_flags, "01");
    }

    #[test]
    fn rejects_invalid_traceparent() {
        assert!(parse_traceparent("invalid").is_none());
    }
}
