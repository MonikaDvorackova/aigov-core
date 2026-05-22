//! GovAI audit service library. Binary entrypoint: [`run`].

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

pub mod ai_decision_audit;
pub mod ai_decision_http;
pub mod ai_decision_integrity;
pub mod api_error;
pub mod api_usage;
pub mod audit_api_key;
pub mod hosted_provisioning;
pub mod auth;
pub mod autonomous_runtime;
pub mod billing_trace;
pub mod contracts;
pub mod db;
pub mod evidence_usage;
pub mod govai_api;
pub mod govai_functions_v2;
pub mod http_observability;
pub mod metering;
pub mod onboarding;
pub mod onboarding_http;
pub mod ops_log;
pub mod pricing;
pub mod product_ops;
pub mod project;
pub mod rate_limit;
pub mod rbac;
pub mod runtime_metrics;
pub mod stripe_billing;
pub mod stripe_webhook;
pub mod tenant_api_keys;
pub mod tenant_console_contract;
pub mod tenant_http;
pub mod tenant_registry;

use axum::middleware;
use axum::Router;
use std::net::SocketAddr;

use crate::govai_environment::GovaiEnvironment;

const LOG_PATH: &str = "audit_log.jsonl";

fn default_bind() -> SocketAddr {
    SocketAddr::from(([127, 0, 0, 1], 8088))
}

fn bind_addr_from_env() -> Result<SocketAddr, String> {
    if let Ok(raw) = std::env::var("AIGOV_BIND") {
        let trimmed = raw.trim();
        if !trimmed.is_empty() {
            return trimmed.parse::<SocketAddr>().map_err(|e| {
                format!(
                    "Invalid AIGOV_BIND {trimmed:?}: {e}. Use a valid host:port (e.g. \"0.0.0.0:8088\"), or unset/whitespace-only AIGOV_BIND to fall back to PORT / the default bind."
                )
            });
        }
    }

    if let Ok(port_s) = std::env::var("PORT") {
        if let Ok(port) = port_s.parse::<u16>() {
            return Ok(SocketAddr::from(([0, 0, 0, 0], port)));
        }
    }

    Ok(default_bind())
}

pub(crate) fn staging_prod_bind_must_be_reachable(
    deployment_env: GovaiEnvironment,
    addr: SocketAddr,
) -> Result<(), String> {
    match deployment_env {
        GovaiEnvironment::Staging | GovaiEnvironment::Prod if addr.ip().is_loopback() => Err(format!(
            "Refusing to start {deployment_env} on loopback {addr}: use a reachable bind address such as \"0.0.0.0:${{PORT}}\" (Railway provides PORT)."
        )),
        _ => Ok(()),
    }
}

async fn assert_staging_prod_operational_constraints(
    deployment_env: GovaiEnvironment,
    addr: SocketAddr,
    auto_migrate: bool,
    pool: &db::DbPool,
) -> Result<(), String> {
    match deployment_env {
        GovaiEnvironment::Dev => Ok(()),
        GovaiEnvironment::Staging | GovaiEnvironment::Prod => {
            staging_prod_bind_must_be_reachable(deployment_env, addr)?;
            if !auto_migrate {
                db::verify_sqlx_migrations_complete(pool).await?;
            }
            Ok(())
        }
    }
}

/// Run the HTTP server (same as the `aigov_audit` binary).
pub async fn run() -> Result<(), String> {
    let addr = match bind_addr_from_env() {
        Ok(a) => a,
        Err(e) => {
            eprintln!("{e}");
            return Err(e);
        }
    };

    let deployment_env = match govai_environment::resolve_from_env() {
        Ok(e) => e,
        Err(e) => {
            eprintln!("{}", e);
            return Err(e);
        }
    };

    if let Err(e) = crate::audit_api_key::init_api_key_tenant_map(deployment_env) {
        eprintln!("{e}");
        return Err(e);
    }

    // Operator footgun guard (cf. INVALID_API_KEY in CI): every key declared in
    // `GOVAI_API_KEYS_JSON` (ledger tenant mapping) must also be present in `GOVAI_API_KEYS`
    // (bearer allowlist). Fails fast in staging/prod with a redaction-safe error.
    if let Err(e) = crate::audit_api_key::validate_api_key_allowlist_consistency(deployment_env) {
        eprintln!("startup: api_key_allowlist_consistency_failed: {e}");
        return Err(e);
    }

    let ledger_dir_result = crate::ledger_storage::validate_startup(deployment_env)?;
    let ledger_display = ledger_dir_result
        .as_ref()
        .map(|p| p.display().to_string())
        .unwrap_or_else(|| {
            "(unset — evidence files use process working directory; not for staging/prod)"
                .to_string()
        });

    let policy_version = govai_environment::policy_version_for(deployment_env);
    let resolved_policy = match policy_config::load_for_deployment(deployment_env) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("{}", e);
            eprintln!(
                "Fix policy files (policy.<env>.json / policy.json under AIGOV_POLICY_DIR), set AIGOV_POLICY_FILE to a valid file, or for local dev-only relaxed loading unset AIGOV_POLICY_STRICT and use AIGOV_ENVIRONMENT=dev."
            );
            return Err(e);
        }
    };

    let policy_store = match crate::policy_store::PolicyStore::load_for_deployment(
        deployment_env,
        resolved_policy.clone(),
    ) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("{e}");
            return Err(e);
        }
    };

    if let Err(e) = db::postgres_url_configured_nonempty() {
        eprintln!("{e}");
        return Err(e);
    }

    let pool = match db::init_pool_from_env().await {
        Ok(p) => p,
        Err(e) => {
            eprintln!("database connection failed: {}", e);
            eprintln!("Configure GOVAI_DATABASE_URL or DATABASE_URL to a reachable Postgres URL.");
            return Err(e);
        }
    };

    let auto_migrate = std::env::var("GOVAI_AUTO_MIGRATE")
        .ok()
        .map(|s| {
            matches!(
                s.trim().to_ascii_lowercase().as_str(),
                "1" | "true" | "on" | "yes"
            )
        })
        .unwrap_or(false);
    if auto_migrate {
        println!("startup: migrations=applying (GOVAI_AUTO_MIGRATE=true)");
        if let Err(e) = sqlx::migrate!("./migrations").run(&pool).await {
            let raw = e.to_string();
            if raw.contains("_sqlx_migrations_pkey")
                && raw.contains("duplicate key value violates unique constraint")
            {
                eprintln!(
                    "DB migration metadata already contains this migration; verifying schema completeness: {raw}"
                );
                db::verify_sqlx_migrations_complete(&pool).await?;
            } else {
                eprintln!("DB migration failed: {}", e);
                return Err(format!("DB migration failed: {e}"));
            }
        }
    } else if matches!(
        deployment_env,
        GovaiEnvironment::Staging | GovaiEnvironment::Prod
    ) {
        println!("startup: migrations=not auto-applied; verifying schema...");
    } else {
        println!("startup: migrations=not auto-applied (dev); GOVAI_AUTO_MIGRATE not enabled");
    }

    if let Err(e) =
        assert_staging_prod_operational_constraints(deployment_env, addr, auto_migrate, &pool).await
    {
        eprintln!("staging/prod startup validation failed: {e}");
        return Err(e);
    }

    // Provision (key_hash → team_id) billing rows from `GOVAI_API_KEY_BILLING_TEAMS_JSON`.
    // Idempotent upsert; key_hash is the sha256 fingerprint of the raw API key (the same
    // digest as `crate::api_usage::key_fingerprint`). Raw API keys are never stored.
    if let Err(e) =
        crate::metering::provision_api_key_billing_teams_from_env(&pool, deployment_env).await
    {
        eprintln!("startup: api_key_billing_teams_provisioning_failed: {e}");
        return Err(e);
    }

    if crate::audit_api_key::hosted_self_service_enabled() {
        match crate::hosted_provisioning::reload_hosted_api_keys_from_db(&pool).await {
            Ok(n) => println!("startup: hosted_api_keys_loaded count={n}"),
            Err(e) => {
                eprintln!("startup: hosted_api_keys_load_failed: {e}");
                return Err(format!("hosted api key reload failed: {e}"));
            }
        }
    }

    let metering = crate::metering::MeteringConfig::from_env();
    if metering.enabled {
        let keys_ok = std::env::var("GOVAI_API_KEYS")
            .ok()
            .map(|s| !s.trim().is_empty())
            .unwrap_or(false);
        if !keys_ok {
            eprintln!("GOVAI_METERING=on requires a non-empty GOVAI_API_KEYS");
            return Err("GOVAI_METERING=on requires GOVAI_API_KEYS".to_string());
        }
    }

    let api_usage = match api_usage::ApiUsageState::from_env(&pool) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("API usage init failed: {}", e);
            return Err(e);
        }
    };

    let app: Router = Router::new()
        .merge(govai_api::core_router(policy_version, deployment_env))
        .merge(govai_api::audit_router(
            LOG_PATH,
            policy_version,
            deployment_env,
            policy_store,
            api_usage,
            pool.clone(),
            metering,
        ))
        .merge(govai_api::assessments_router(pool.clone()))
        .merge(govai_api::compliance_workflow_router(pool))
        .layer(middleware::from_fn(
            crate::http_observability::observability_middleware,
        ));

    println!(
        "startup: bind=http://{} environment={} policy_version={}",
        addr, deployment_env, policy_version
    );
    println!("startup: ledger_dir={ledger_display}");
    println!("startup: database=verified (pool connected)");
    if auto_migrate {
        println!("startup: migrations=complete (applied this boot)");
    } else if matches!(
        deployment_env,
        GovaiEnvironment::Staging | GovaiEnvironment::Prod
    ) {
        println!("startup: migrations=verified against _sqlx_migrations");
    }
    println!("startup: liveness=GET /health  readiness=GET /ready  metrics=GET /metrics");

    println!("govai listening on http://{}", addr);

    let listener = match tokio::net::TcpListener::bind(addr).await {
        Ok(l) => l,
        Err(e) => {
            eprintln!("Bind failed on {}: {}", addr, e);
            return Err(e.to_string());
        }
    };

    axum::serve(listener, app).await.map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Mutex, OnceLock};

    fn env_lock() -> &'static Mutex<()> {
        static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
        LOCK.get_or_init(|| Mutex::new(()))
    }

    fn clear_env_keys() {
        std::env::remove_var("AIGOV_BIND");
        std::env::remove_var("PORT");
    }

    #[test]
    fn bind_addr_uses_aigov_bind_when_valid() {
        let _g = env_lock().lock().unwrap();
        clear_env_keys();

        std::env::set_var("AIGOV_BIND", "127.0.0.1:5555");
        std::env::set_var("PORT", "9999");

        assert_eq!(
            bind_addr_from_env().unwrap(),
            SocketAddr::from(([127, 0, 0, 1], 5555))
        );
        clear_env_keys();
    }

    #[test]
    fn bind_addr_falls_back_to_port_when_aigov_bind_missing() {
        let _g = env_lock().lock().unwrap();
        clear_env_keys();

        std::env::set_var("PORT", "3000");
        assert_eq!(
            bind_addr_from_env().unwrap(),
            SocketAddr::from(([0, 0, 0, 0], 3000))
        );

        clear_env_keys();
    }

    #[test]
    fn bind_addr_errors_when_aigov_bind_nonempty_invalid() {
        let _g = env_lock().lock().unwrap();
        clear_env_keys();

        std::env::set_var("AIGOV_BIND", "not-a-socket-addr");
        std::env::set_var("PORT", "3001");

        let err = bind_addr_from_env().unwrap_err();
        assert!(err.contains("AIGOV_BIND"), "{err}");
        clear_env_keys();
    }

    #[test]
    fn bind_addr_empty_or_whitespace_aigov_bind_allows_port_fallback() {
        let _g = env_lock().lock().unwrap();
        clear_env_keys();

        std::env::set_var("AIGOV_BIND", "");
        std::env::set_var("PORT", "3002");
        assert_eq!(
            bind_addr_from_env().unwrap(),
            SocketAddr::from(([0, 0, 0, 0], 3002))
        );

        std::env::set_var("AIGOV_BIND", "   \t  ");
        std::env::set_var("PORT", "3003");
        assert_eq!(
            bind_addr_from_env().unwrap(),
            SocketAddr::from(([0, 0, 0, 0], 3003))
        );

        clear_env_keys();
    }

    #[test]
    fn bind_addr_defaults_when_no_env_or_invalid_port() {
        let _g = env_lock().lock().unwrap();
        clear_env_keys();

        assert_eq!(bind_addr_from_env().unwrap(), default_bind());

        std::env::set_var("PORT", "not-a-number");
        assert_eq!(bind_addr_from_env().unwrap(), default_bind());

        clear_env_keys();
    }

    #[test]
    fn staging_rejects_loopback_bind() {
        let addr = SocketAddr::from(([127, 0, 0, 1], 8088));
        let err = staging_prod_bind_must_be_reachable(GovaiEnvironment::Staging, addr).unwrap_err();
        assert!(err.contains("loopback"), "{err}");

        let ok = staging_prod_bind_must_be_reachable(
            GovaiEnvironment::Staging,
            SocketAddr::from(([0, 0, 0, 0], 8088)),
        );
        assert!(ok.is_ok());
    }

    #[test]
    fn dev_allows_loopback_bind() {
        let addr = SocketAddr::from(([127, 0, 0, 1], 8088));
        assert!(staging_prod_bind_must_be_reachable(GovaiEnvironment::Dev, addr).is_ok());
    }
}
