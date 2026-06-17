//! HTTP middleware: bounded Prometheus route keys + latency + coarse error accounting.

use axum::body::Body;
use axum::http::{Method, Request, StatusCode};
use axum::middleware::Next;
use axum::response::Response;
use std::time::Instant;

/// Normalize dynamic path segments so metrics labels stay bounded and non-identifying.
pub fn route_metric_key(method: &Method, path: &str) -> String {
    let p = path.split('?').next().unwrap_or(path);
    let mut out = String::new();
    out.push_str(method.as_str());
    out.push(' ');
    if p == "/" || p.is_empty() {
        out.push('/');
        return out;
    }
    if p == "/health" {
        out.push_str("/health");
        return out;
    }
    if p == "/ready" {
        out.push_str("/ready");
        return out;
    }
    if p == "/metrics" {
        out.push_str("/metrics");
        return out;
    }
    if p == "/status" {
        out.push_str("/status");
        return out;
    }
    if p == "/evidence" {
        out.push_str("/evidence");
        return out;
    }
    if p == "/compliance-summary" {
        out.push_str("/compliance-summary");
        return out;
    }
    if p == "/verify" || p == "/verify-log" || p == "/verify-immutable" {
        out.push_str(p);
        return out;
    }
    if p.starts_with("/bundle") {
        out.push_str("/bundle");
        return out;
    }
    if p.starts_with("/bundle-hash") {
        out.push_str("/bundle-hash");
        return out;
    }
    if p.starts_with("/api/export/") {
        out.push_str("/api/export/{run_id}");
        return out;
    }
    if p.starts_with("/api/ai-decision-traces/") && p.ends_with("/events") {
        out.push_str("/api/ai-decision-traces/{run_id}/events");
        return out;
    }
    if p.starts_with("/api/ai-decision-traces") {
        out.push_str("/api/ai-decision-traces");
        return out;
    }
    if p.starts_with("/api/tenant-console") {
        out.push_str("/api/tenant-console/...");
        return out;
    }
    if p.starts_with("/api/me") {
        out.push_str("/api/me");
        return out;
    }
    if p.starts_with("/v1/runtime/evaluate") {
        out.push_str("/v1/runtime/evaluate");
        return out;
    }
    if p.starts_with("/usage") {
        out.push_str("/usage");
        return out;
    }
    // Fallback: first two segments only
    let parts: Vec<&str> = p.split('/').filter(|s| !s.is_empty()).collect();
    out.push('/');
    if let Some(a) = parts.first() {
        out.push_str(a);
    }
    if let Some(b) = parts.get(1) {
        out.push('/');
        out.push_str(b);
        if parts.len() > 2 {
            out.push_str("/...");
        }
    }
    out
}

pub async fn observability_middleware(request: Request<Body>, next: Next) -> Response {
    let method = request.method().clone();
    let path = request.uri().path().to_string();
    let key = route_metric_key(&method, &path);
    let started = Instant::now();
    let response = next.run(request).await;
    let status = response.status();
    let code = status.as_u16();
    let elapsed = started.elapsed().as_secs_f64();
    crate::runtime_metrics::record_http_request(&key, code, elapsed);

    if path == "/evidence" && method == Method::POST {
        let outcome = if code == 200 { "accepted" } else { "rejected" };
        crate::runtime_metrics::inc_evidence_ingest(outcome);
        crate::ops_log::evidence_ingest(outcome, code, "api_key_derived");
    }

    response
}

pub async fn metrics_handler() -> Response {
    let body = crate::runtime_metrics::render_prometheus_text();
    Response::builder()
        .status(StatusCode::OK)
        .header(
            axum::http::header::CONTENT_TYPE,
            "text/plain; version=0.0.4; charset=utf-8",
        )
        .body(Body::from(body))
        .unwrap_or_else(|_| {
            Response::builder()
                .status(StatusCode::INTERNAL_SERVER_ERROR)
                .body(Body::from("metrics encoding error"))
                .unwrap()
        })
}
