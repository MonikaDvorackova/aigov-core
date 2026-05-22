use axum::http::{HeaderMap, StatusCode};
use axum::Json;
use jsonwebtoken::{decode, decode_header, Algorithm, DecodingKey, TokenData, Validation};
use once_cell::sync::OnceCell;
use serde::Deserialize;
use std::time::{Duration, Instant};
use uuid::Uuid;

use crate::api_error::api_error;

#[derive(Clone)]
pub struct AuthConfig {
    pub supabase_url: String,
    pub issuer: String,
    pub audience: Option<String>,
}

impl AuthConfig {
    pub fn from_env() -> Result<Self, String> {
        let supabase_url =
            std::env::var("SUPABASE_URL").map_err(|_| "SUPABASE_URL missing".to_string())?;
        let issuer = format!("{}/auth/v1", supabase_url.trim_end_matches('/'));
        let audience = std::env::var("SUPABASE_JWT_AUD").ok();

        Ok(Self {
            supabase_url,
            issuer,
            audience,
        })
    }

    pub fn jwks_url(&self) -> String {
        format!(
            "{}/auth/v1/.well-known/jwks.json",
            self.supabase_url.trim_end_matches('/')
        )
    }
}

#[derive(Debug, Clone)]
pub struct CurrentUser {
    pub user_id: Uuid,
}

#[derive(Debug, Deserialize)]
struct Claims {
    sub: String,
    iss: String,
    aud: Option<serde_json::Value>,
    exp: usize,
}

#[derive(Debug, Deserialize, Clone)]
struct Jwks {
    keys: Vec<Jwk>,
}

#[derive(Debug, Deserialize, Clone)]
struct Jwk {
    kid: String,
    kty: String,
    n: String,
    e: String,
}

struct CachedJwks {
    jwks_url: String,
    fetched_at: Instant,
    jwks: Jwks,
}

static JWKS_CACHE: OnceCell<tokio::sync::RwLock<Option<CachedJwks>>> = OnceCell::new();

async fn get_jwks(cfg: &AuthConfig) -> Result<Jwks, String> {
    let lock = JWKS_CACHE.get_or_init(|| tokio::sync::RwLock::new(None));
    let want_url = cfg.jwks_url();

    {
        let read = lock.read().await;
        if let Some(cached) = &*read {
            if cached.jwks_url == want_url && cached.fetched_at.elapsed() < Duration::from_secs(300) {
                return Ok(cached.jwks.clone());
            }
        }
    }

    let resp = reqwest::get(&want_url)
        .await
        .map_err(|e| format!("JWKS fetch failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("JWKS fetch status: {}", resp.status()));
    }

    let jwks: Jwks = resp
        .json()
        .await
        .map_err(|e| format!("JWKS parse failed: {}", e))?;

    let mut write = lock.write().await;
    *write = Some(CachedJwks {
        jwks_url: want_url,
        fetched_at: Instant::now(),
        jwks: jwks.clone(),
    });

    Ok(jwks)
}

fn pick_decoding_key(jwks: &Jwks, kid: &str) -> Result<DecodingKey, String> {
    let key = jwks
        .keys
        .iter()
        .find(|k| k.kid == kid)
        .ok_or_else(|| "JWT kid not found in JWKS".to_string())?;

    if key.kty != "RSA" {
        return Err("Unsupported JWK kty".to_string());
    }

    DecodingKey::from_rsa_components(&key.n, &key.e)
        .map_err(|e| format!("DecodingKey error: {}", e))
}

fn aud_ok(claims: &Claims, expected: &Option<String>) -> bool {
    let Some(exp) = expected else { return true };
    let Some(aud) = &claims.aud else { return false };

    match aud {
        serde_json::Value::String(s) => s == exp,
        serde_json::Value::Array(arr) => arr.iter().any(|v| v.as_str() == Some(exp.as_str())),
        _ => false,
    }
}

pub async fn require_user(
    cfg: &AuthConfig,
    headers: &HeaderMap,
) -> Result<CurrentUser, (StatusCode, Json<serde_json::Value>)> {
    let auth = headers
        .get(axum::http::header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");

    let token = auth.strip_prefix("Bearer ").unwrap_or("").trim();
    if token.is_empty() {
        return Err(api_error(
            StatusCode::UNAUTHORIZED,
            "MISSING_AUTH_TOKEN",
            "Missing Authorization bearer token.",
            "Provide `Authorization: Bearer <access_token>` (Supabase JWT).",
            None,
        ));
    }

    let header = decode_header(token).map_err(|_| {
        api_error(
            StatusCode::UNAUTHORIZED,
            "INVALID_AUTH_TOKEN",
            "Invalid JWT.",
            "Ensure the token is a valid, unexpired Supabase access token (JWT).",
            None,
        )
    })?;

    let kid = header.kid.ok_or_else(|| {
        api_error(
            StatusCode::UNAUTHORIZED,
            "INVALID_AUTH_TOKEN",
            "Invalid JWT.",
            "Ensure the token is a valid Supabase access token (JWT).",
            None,
        )
    })?;

    let jwks = get_jwks(cfg).await.map_err(|e| {
        api_error(
            StatusCode::INTERNAL_SERVER_ERROR,
            "JWKS_UNAVAILABLE",
            "We could not validate the JWT because the JWKS could not be loaded.",
            "Retry in a moment. If this persists, contact support (this is a server-side issue).",
            Some(serde_json::Value::String(e)),
        )
    })?;

    let key = pick_decoding_key(&jwks, &kid).map_err(|e| {
        api_error(
            StatusCode::UNAUTHORIZED,
            "INVALID_AUTH_TOKEN",
            "Invalid JWT.",
            "Ensure the token is a valid Supabase access token (JWT).",
            Some(serde_json::Value::String(e)),
        )
    })?;

    let mut validation = Validation::new(Algorithm::RS256);
    validation.validate_exp = true;
    validation.set_issuer(&[cfg.issuer.as_str()]);
    validation.validate_aud = false;

    let data: TokenData<Claims> = decode(token, &key, &validation).map_err(|_| {
        api_error(
            StatusCode::UNAUTHORIZED,
            "INVALID_AUTH_TOKEN",
            "Invalid JWT.",
            "Ensure the token is a valid, unexpired Supabase access token (JWT).",
            None,
        )
    })?;

    // Explicit read to avoid dead_code warning
    let _ = data.claims.exp;

    if data.claims.iss != cfg.issuer {
        return Err(api_error(
            StatusCode::UNAUTHORIZED,
            "INVALID_JWT_ISSUER",
            "JWT issuer does not match the configured Supabase issuer.",
            "Use an access token issued by this project's Supabase instance.",
            None,
        ));
    }

    if !aud_ok(&data.claims, &cfg.audience) {
        return Err(api_error(
            StatusCode::UNAUTHORIZED,
            "INVALID_JWT_AUDIENCE",
            "JWT audience does not match the configured audience.",
            "Request a token with the correct audience for this API.",
            None,
        ));
    }

    let user_id = Uuid::parse_str(&data.claims.sub).map_err(|_| {
        api_error(
            StatusCode::UNAUTHORIZED,
            "INVALID_JWT_SUBJECT",
            "JWT subject (sub) is invalid.",
            "Re-authenticate and retry with a fresh access token.",
            None,
        )
    })?;

    Ok(CurrentUser { user_id })
}
