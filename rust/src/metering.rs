//! Optional billable-run metering on evidence ingest (`GOVAI_METERING=on`).
//!
//! Core audit runtime does not implement Stripe or SaaS billing; this module only
//! exposes deterministic counters for operator diagnostics when explicitly enabled.

use serde_json::{json, Value};

pub fn metering_enabled() -> bool {
    matches!(
        std::env::var("GOVAI_METERING")
            .map(|s| s.trim().to_ascii_lowercase())
            .unwrap_or_default()
            .as_str(),
        "1" | "true" | "yes" | "on"
    )
}

/// Extra JSON fields merged into successful `POST /evidence` responses when metering is on.
pub fn ingest_success_extras(tenant_id: &str, run_id: &str, pre_append_event_count: u64) -> Value {
    json!({
        "metering": "on",
        "ledger_tenant_id": tenant_id,
        "run_id": run_id,
        "run_event_count_before_append": pre_append_event_count,
        "run_event_count_after_append": pre_append_event_count.saturating_add(1),
    })
}
