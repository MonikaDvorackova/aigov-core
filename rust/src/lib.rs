pub mod audit_store;
pub mod bundle;
pub mod govai_environment;
pub mod immutable_store;
pub mod ledger_storage;
pub mod policy;
pub mod policy_config;
pub mod policy_engine;
pub mod policy_signing;
pub mod policy_store;
pub mod schema;
pub mod verify_chain;
pub mod projection;

pub mod compliance_summary;
pub mod audit_export;
pub mod replay_validation;
pub mod replay_projection;
pub mod replay_engine;
pub mod ledger_view;
pub mod metering;
pub mod govai_api;

pub mod ai_decision_audit;
pub mod ai_decision_integrity;

pub mod api_error;
pub mod audit_api_key;
pub mod auth;
pub mod contracts;
pub mod db;
pub mod http_observability;
pub mod ops_log;
pub mod project;
pub mod rate_limit;
pub mod rbac;
pub mod runtime_metrics;

pub mod api_usage;
pub mod tenant_api_keys;

pub use govai_api::{build_app_state, build_router};

/// Start the audit HTTP server (bind address from `AIGOV_BIND`, default `127.0.0.1:8088`).
pub async fn run() -> Result<(), String> {
    let bind = std::env::var("AIGOV_BIND").unwrap_or_else(|_| "127.0.0.1:8088".to_string());
    let state = build_app_state().await?;
    let app = build_router(state);
    let listener = tokio::net::TcpListener::bind(&bind)
        .await
        .map_err(|e| format!("bind {bind}: {e}"))?;
    eprintln!("govai listening on http://{bind}");
    axum::serve(listener, app)
        .await
        .map_err(|e| format!("server error: {e}"))?;
    Ok(())
}
