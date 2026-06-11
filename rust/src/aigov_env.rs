//! Environment variables: prefer `AIGOV_*`, fall back to legacy `GOVAI_*`.

use std::env::{self, VarError};

fn nonempty(value: String) -> Option<String> {
    if value.trim().is_empty() {
        None
    } else {
        Some(value)
    }
}

/// First non-empty value among `AIGOV_*` then `GOVAI_*` for the same suffix.
pub fn optional(aigov_key: &str, govai_key: &str) -> Option<String> {
    env::var(aigov_key)
        .ok()
        .and_then(nonempty)
        .or_else(|| env::var(govai_key).ok().and_then(nonempty))
}

/// Like [`optional`], but returns `VarError::NotPresent` when neither key is set.
pub fn required(aigov_key: &str, govai_key: &str) -> Result<String, VarError> {
    optional(aigov_key, govai_key).ok_or(VarError::NotPresent)
}

/// First non-empty value from an ordered key list (e.g. AIGOV and GOVAI Stripe price aliases).
pub fn first_present(keys: &[&str]) -> Option<String> {
    keys.iter()
        .find_map(|key| env::var(key).ok().and_then(nonempty))
}

/// Postgres URL: `AIGOV_DATABASE_URL` → `GOVAI_DATABASE_URL` → `DATABASE_URL`.
pub fn database_url_optional() -> Option<String> {
    optional("AIGOV_DATABASE_URL", "GOVAI_DATABASE_URL")
        .or_else(|| env::var("DATABASE_URL").ok().and_then(nonempty))
}

/// Required Postgres URL (see [`database_url_optional`]).
pub fn database_url() -> Result<String, String> {
    database_url_optional().ok_or_else(|| {
        "Missing Postgres URL: set AIGOV_DATABASE_URL or GOVAI_DATABASE_URL (legacy) or DATABASE_URL."
            .to_string()
    })
}

/// True when the resolved value is `1`, `true`, `on`, or `yes` (case-insensitive).
pub fn flag_truthy(aigov_key: &str, govai_key: &str) -> bool {
    optional(aigov_key, govai_key)
        .map(|s| {
            matches!(
                s.trim().to_ascii_lowercase().as_str(),
                "1" | "true" | "on" | "yes"
            )
        })
        .unwrap_or(false)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Mutex, MutexGuard};

    static ENV_LOCK: Mutex<()> = Mutex::new(());

    fn env_lock() -> MutexGuard<'static, ()> {
        ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner())
    }

    #[test]
    fn optional_prefers_aigov_over_govai() {
        let _g = env_lock();
        std::env::set_var("AIGOV_SKIP_FSYNC", "1");
        std::env::set_var("GOVAI_SKIP_FSYNC", "0");
        assert_eq!(
            optional("AIGOV_SKIP_FSYNC", "GOVAI_SKIP_FSYNC").as_deref(),
            Some("1")
        );
        std::env::remove_var("AIGOV_SKIP_FSYNC");
        assert_eq!(
            optional("AIGOV_SKIP_FSYNC", "GOVAI_SKIP_FSYNC").as_deref(),
            Some("0")
        );
        std::env::remove_var("GOVAI_SKIP_FSYNC");
    }

    #[test]
    fn flag_truthy_accepts_on_and_yes() {
        let _g = env_lock();
        std::env::set_var("AIGOV_AUTO_MIGRATE", "on");
        assert!(flag_truthy("AIGOV_AUTO_MIGRATE", "GOVAI_AUTO_MIGRATE"));
        std::env::remove_var("AIGOV_AUTO_MIGRATE");
    }
}
