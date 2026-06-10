//! Non-sensitive runtime diagnostics for `/status` (operator visibility).

use crate::audit_api_key::AuditApiKeyConfig;
use crate::db;
use crate::ledger_storage;
use crate::policy_config::{PolicySource, PolicySourceKind};
use crate::govai_api::AppState;
use serde_json::{json, Value};
use std::path::{Component, Path};
use std::time::{Instant, SystemTime, UNIX_EPOCH};

/// Process start time for uptime reporting.
#[derive(Clone, Copy)]
pub struct ProcessStartedAt(pub Instant);

impl ProcessStartedAt {
    pub fn now() -> Self {
        Self(Instant::now())
    }

    pub fn uptime_seconds(&self) -> f64 {
        self.0.elapsed().as_secs_f64()
    }

    pub fn started_at_utc_rfc3339(&self) -> String {
        let elapsed = self.0.elapsed();
        SystemTime::now()
            .checked_sub(elapsed)
            .unwrap_or(UNIX_EPOCH)
            .duration_since(UNIX_EPOCH)
            .map(|d| {
                chrono::DateTime::<chrono::Utc>::from(UNIX_EPOCH + d)
                    .to_rfc3339_opts(chrono::SecondsFormat::Secs, true)
            })
            .unwrap_or_else(|_| "unknown".to_string())
    }
}

/// Redact path for status output: basename only, or last two components when safe.
pub fn redact_path_label(path: &Path) -> String {
    let parts: Vec<&str> = path
        .components()
        .filter_map(|c| match c {
            Component::Normal(s) => s.to_str(),
            Component::CurDir => Some("."),
            Component::ParentDir => Some(".."),
            _ => None,
        })
        .collect();
    if parts.is_empty() {
        return "<unset>".to_string();
    }
    if parts.len() <= 2 {
        return parts.join("/");
    }
    parts[parts.len() - 2..].join("/")
}

fn env_configured(name: &str) -> bool {
    std::env::var(name)
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false)
}

pub fn runtime_governance_enforcement_diag() -> Value {
    let raw = std::env::var("GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT")
        .unwrap_or_default()
        .trim()
        .to_ascii_lowercase();
    let configured = match raw.as_str() {
        "shadow" => "shadow",
        "enforced" => "enforced",
        _ => "off",
    };
    let tenants_raw =
        std::env::var("GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT_TENANTS").unwrap_or_default();
    let tenant_allowlist_configured = tenants_raw
        .split(',')
        .map(|s| s.trim())
        .any(|s| !s.is_empty());
    let enforceable = configured == "enforced" && tenant_allowlist_configured;
    let reason_if_not_enforceable = if enforceable {
        Value::Null
    } else if configured != "enforced" {
        Value::String("configured_mode is not enforced".to_string())
    } else {
        Value::String("tenant allowlist empty".to_string())
    };
    json!({
        "mode": configured,
        "configured_mode": configured,
        "tenant_allowlist_configured": tenant_allowlist_configured,
        "enforceable": enforceable,
        "reason_if_not_enforceable": reason_if_not_enforceable,
    })
}

fn policy_source_kind_label(kind: PolicySourceKind) -> &'static str {
    match kind {
        PolicySourceKind::OverrideFile => "override_file",
        PolicySourceKind::EnvFile => "env_file",
        PolicySourceKind::FallbackFile => "fallback_file",
        PolicySourceKind::Defaults => "defaults",
    }
}

pub fn signing_trust_configured() -> bool {
    let raw = std::env::var("AIGOV_POLICY_TRUST_ED25519_JSON").unwrap_or_default();
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return false;
    }
    serde_json::from_str::<Value>(trimmed)
        .ok()
        .filter(|v| {
            v.as_array()
                .map(|a| !a.is_empty())
                .unwrap_or(false)
        })
        .is_some()
}

pub fn api_key_allowlist_count(cfg: &AuditApiKeyConfig) -> u64 {
    cfg.keys
        .as_ref()
        .map(|m| m.len() as u64)
        .unwrap_or(0)
}

pub fn api_key_tenant_map_count() -> u64 {
    let raw = std::env::var("GOVAI_API_KEYS_JSON").unwrap_or_default();
    if raw.trim().is_empty() {
        return 0;
    }
    serde_json::from_str::<serde_json::Map<String, Value>>(&raw)
        .map(|m| m.len() as u64)
        .unwrap_or(0)
}

pub fn configuration_block(st: &AppState, policy_source: &PolicySource) -> Value {
    let ledger_configured = ledger_storage::configured_ledger_dir().is_some();
    let ledger_label = ledger_storage::configured_ledger_dir()
        .map(|p| redact_path_label(&p))
        .unwrap_or_else(|| "<ephemeral cwd>".to_string());

    let policy_dir_configured = env_configured("AIGOV_POLICY_DIR");
    let policy_dir_label = std::env::var("AIGOV_POLICY_DIR")
        .ok()
        .filter(|s| !s.trim().is_empty())
        .map(|s| redact_path_label(Path::new(s.trim())))
        .unwrap_or_else(|| "default_search".to_string());

    json!({
        "ledger_dir_configured": ledger_configured,
        "ledger_dir_label": ledger_label,
        "database_configured": db::postgres_url_configured_nonempty().is_ok(),
        "policy_dir_configured": policy_dir_configured,
        "policy_dir_label": policy_dir_label,
        "policy_source_kind": policy_source_kind_label(policy_source.kind),
        "policy_source_path": policy_source.path,
        "api_key_allowlist_count": api_key_allowlist_count(&st.api_key_cfg),
        "api_key_tenant_map_count": api_key_tenant_map_count(),
        "signing_trust_configured": signing_trust_configured(),
        "aigov_bind_configured": env_configured("AIGOV_BIND"),
    })
}

pub async fn readiness_components(st: &AppState, include_ledger_probe: bool) -> Value {
    let db_configured = db::postgres_url_configured_nonempty().is_ok();
    let mut database_ping = !db_configured;
    let mut migrations_complete = !db_configured;
    let mut migration_status = Value::String(if db_configured {
        "unknown".to_string()
    } else {
        "not_configured".to_string()
    });

    if db_configured {
        database_ping = sqlx::query_scalar::<_, i32>("select 1")
            .fetch_one(&st.pool)
            .await
            .is_ok();
        if database_ping {
            match db::verify_sqlx_migrations_complete(&st.pool).await {
                Ok(()) => {
                    migrations_complete = true;
                    migration_status = json!("complete");
                }
                Err(e) => {
                    migrations_complete = false;
                    migration_status = json!({
                        "state": "pending_or_failed",
                        "detail_redacted": crate::ops_log::redact_diagnostic_message(&e),
                    });
                }
            }
        } else {
            migration_status = json!({
                "state": "database_unreachable",
            });
        }
    }

    let ledger_writable = ledger_storage::validate_startup(st.deployment_env)
        .map(|_| true)
        .unwrap_or(false);

    let mut tenant_ledger_probe = Value::Null;
    if include_ledger_probe && ledger_writable {
        let probe_path = crate::project::resolve_ledger_path("audit_log.jsonl", "__ready_probe__");
        let probe = crate::schema::EvidenceEvent {
            event_id: format!("ready-probe-{}", uuid::Uuid::new_v4()),
            event_type: "ai_discovery_reported".to_string(),
            ts_utc: chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true),
            actor: "ready_probe".to_string(),
            system: "govai".to_string(),
            run_id: format!("ready-probe-{}", uuid::Uuid::new_v4()),
            environment: Some(st.deployment_env.as_str().to_string()),
            payload: json!({
                "openai": false,
                "transformers": false,
                "model_artifacts": false,
                "status": "probe",
            }),
            payload: json!({
                "openai": false,
                "transformers": false,
                "model_artifacts": false,
                "status": "probe",
            }),
            parent_run_id: None,
            root_run_id: None,
            delegated_from_event_id: None,
            agent_id: None,
            agent_role: None,
            delegation_reason: None,
        };
        };
        let ok =
            crate::audit_store::append_record_atomic_with_run_count(&probe_path, probe).is_ok();
        tenant_ledger_probe = json!(ok);
    }

    json!({
        "database_ping": database_ping,
        "migrations_complete": migrations_complete,
        "migration_status": migration_status,
        "ledger_writable": ledger_writable,
        "tenant_ledger_probe": tenant_ledger_probe,
    })
}

pub fn otel_hooks_block() -> Value {
    json!({
        "w3c_trace_context": true,
        "traceparent_header": "traceparent",
        "evidence_payload_field": "external_trace",
        "documentation": "docs/runtime-observability.md#opentelemetry-and-trace-linking",
        "sdk_required": false,
    })
}

pub async fn build_status_body(
    st: &AppState,
    started: ProcessStartedAt,
    policy_source: &PolicySource,
) -> Value {
    let components = readiness_components(st, false).await;
    let db_ping = components
        .get("database_ping")
        .and_then(|v| v.as_bool())
        .unwrap_or(true);
    let migrations_ok = components
        .get("migrations_complete")
        .and_then(|v| v.as_bool())
        .unwrap_or(true);
    let ledger_ok = components
        .get("ledger_writable")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    let operational_ready = db_ping && migrations_ok && ledger_ok;

    let mut body = json!({
        "ok": true,
        "service": "aigov_audit",
        "surface": "govai-core",
        "runtime_version": env!("CARGO_PKG_VERSION"),
        "environment": st.deployment_env.as_str(),
        "policy_version": crate::govai_environment::policy_version_for(st.deployment_env),
        "uptime_seconds": started.uptime_seconds(),
        "started_at_utc": started.started_at_utc_rfc3339(),
        "operational_ready": operational_ready,
        "configuration": configuration_block(st, policy_source),
        "readiness_components": components,
        "runtime_governance_enforcement": runtime_governance_enforcement_diag(),
        "otel": otel_hooks_block(),
    });
    if let Some(ref u) = st.base_url {
        body["base_url"] = json!(u);
    }
    body
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn redact_path_label_hides_prefix() {
        let p = Path::new("/var/lib/govai/ledger");
        assert_eq!(redact_path_label(p), "govai/ledger");
    }

    #[test]
    fn signing_trust_empty_is_false() {
        std::env::remove_var("AIGOV_POLICY_TRUST_ED25519_JSON");
        assert!(!signing_trust_configured());
    }
}
