use axum::http::StatusCode;
use axum::Json;
use serde_json::json;

/// Standard customer-facing error shape for all JSON APIs.
///
/// Contract:
/// - `ok`: always `false` for error responses (kept for backward compatibility)
/// - `error.code`: stable machine-readable discriminator (SCREAMING_SNAKE_CASE)
/// - `error.message`: user-facing short message
/// - `error.hint`: actionable next step for self-service recovery
/// - `error.details`: optional structured data (safe to expose)
pub fn api_error(
    status: StatusCode,
    code: &str,
    message: &str,
    hint: &str,
    details: Option<serde_json::Value>,
) -> (StatusCode, Json<serde_json::Value>) {
    let mut err = serde_json::Map::new();
    err.insert(
        "code".to_string(),
        serde_json::Value::String(code.to_string()),
    );
    err.insert(
        "message".to_string(),
        serde_json::Value::String(message.to_string()),
    );
    err.insert(
        "hint".to_string(),
        serde_json::Value::String(hint.to_string()),
    );
    if let Some(d) = details {
        err.insert("details".to_string(), d);
    }

    (
        status,
        Json(json!({
            "ok": false,
            "error": serde_json::Value::Object(err),
        })),
    )
}

/// Like [`api_error`] but merges extra top-level fields into the response.
pub fn api_error_with(
    status: StatusCode,
    code: &str,
    message: &str,
    hint: &str,
    details: Option<serde_json::Value>,
    extra_top_level: Option<serde_json::Value>,
) -> (StatusCode, Json<serde_json::Value>) {
    let (status, Json(mut v)) = api_error(status, code, message, hint, details);
    if let Some(extra) = extra_top_level {
        if let (serde_json::Value::Object(ref mut base), serde_json::Value::Object(obj)) =
            (&mut v, extra)
        {
            for (k, val) in obj {
                base.insert(k, val);
            }
        }
    }
    (status, Json(v))
}
