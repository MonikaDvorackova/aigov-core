//! Prometheus-style counters for the audit HTTP surface (no secrets in labels).
//!
//! Cardinality is bounded via [`crate::http_observability::route_metric_key`].

use std::collections::HashMap;
use std::sync::atomic::{AtomicI64, AtomicU64, Ordering};
use std::sync::Mutex;

static HTTP_REQUESTS: AtomicU64 = AtomicU64::new(0);
static HTTP_ERRORS: AtomicU64 = AtomicU64::new(0);
static HTTP_DURATION_SUM_NS: AtomicU64 = AtomicU64::new(0);
static HTTP_DURATION_COUNT: AtomicU64 = AtomicU64::new(0);

static EVIDENCE_INGEST_ACCEPTED: AtomicU64 = AtomicU64::new(0);
static EVIDENCE_INGEST_REJECTED: AtomicU64 = AtomicU64::new(0);
static COMPLIANCE_SUMMARY: AtomicU64 = AtomicU64::new(0);
static AI_TRACE_EVENTS: AtomicU64 = AtomicU64::new(0);

static READINESS_OK: AtomicI64 = AtomicI64::new(-1);
static HEALTH_OK: AtomicI64 = AtomicI64::new(-1);

struct RouteStats {
    count: AtomicU64,
    sum_ns: AtomicU64,
    errors: AtomicU64,
}

type PerRoute = Mutex<HashMap<String, RouteStats>>;

fn per_route() -> &'static PerRoute {
    static MAP: std::sync::OnceLock<PerRoute> = std::sync::OnceLock::new();
    MAP.get_or_init(|| Mutex::new(HashMap::new()))
}

pub fn record_http_request(route_key: &str, status: u16, duration_secs: f64) {
    HTTP_REQUESTS.fetch_add(1, Ordering::Relaxed);
    let ns = (duration_secs * 1_000_000_000.0).max(0.0) as u64;
    HTTP_DURATION_SUM_NS.fetch_add(ns, Ordering::Relaxed);
    HTTP_DURATION_COUNT.fetch_add(1, Ordering::Relaxed);
    if status >= 400 {
        HTTP_ERRORS.fetch_add(1, Ordering::Relaxed);
    }

    let mut map = per_route().lock().expect("metrics route map poisoned");
    let e = map.entry(route_key.to_string()).or_insert_with(|| RouteStats {
        count: AtomicU64::new(0),
        sum_ns: AtomicU64::new(0),
        errors: AtomicU64::new(0),
    });
    e.count.fetch_add(1, Ordering::Relaxed);
    e.sum_ns.fetch_add(ns, Ordering::Relaxed);
    if status >= 400 {
        e.errors.fetch_add(1, Ordering::Relaxed);
    }
}

pub fn inc_evidence_ingest(outcome: &str) {
    match outcome {
        "accepted" => {
            EVIDENCE_INGEST_ACCEPTED.fetch_add(1, Ordering::Relaxed);
        }
        _ => {
            EVIDENCE_INGEST_REJECTED.fetch_add(1, Ordering::Relaxed);
        }
    }
}

pub fn inc_compliance_summary() {
    COMPLIANCE_SUMMARY.fetch_add(1, Ordering::Relaxed);
}

pub fn inc_ai_trace_event() {
    AI_TRACE_EVENTS.fetch_add(1, Ordering::Relaxed);
}

pub fn set_readiness_ready(ok: bool) {
    READINESS_OK.store(if ok { 1 } else { 0 }, Ordering::Relaxed);
}

pub fn set_health_ok(ok: bool) {
    HEALTH_OK.store(if ok { 1 } else { 0 }, Ordering::Relaxed);
}

fn fmt_u64(w: &mut String, name: &str, help: &str, typ: &str, v: u64) {
    w.push_str("# HELP ");
    w.push_str(name);
    w.push(' ');
    w.push_str(help);
    w.push('\n');
    w.push_str("# TYPE ");
    w.push_str(name);
    w.push(' ');
    w.push_str(typ);
    w.push('\n');
    w.push_str(name);
    w.push(' ');
    w.push_str(&v.to_string());
    w.push('\n');
}

fn fmt_i64_gauge(w: &mut String, name: &str, help: &str, v: i64) {
    w.push_str("# HELP ");
    w.push_str(name);
    w.push(' ');
    w.push_str(help);
    w.push('\n');
    w.push_str("# TYPE ");
    w.push_str(name);
    w.push_str(" gauge\n");
    w.push_str(name);
    w.push(' ');
    w.push_str(&v.to_string());
    w.push('\n');
}

/// Prometheus exposition (text format 0.0.4). No labels containing user data.
pub fn render_prometheus_text() -> String {
    let mut out = String::new();
    fmt_u64(
        &mut out,
        "govai_http_requests_total",
        "Total HTTP requests handled by the GovAI audit process.",
        "counter",
        HTTP_REQUESTS.load(Ordering::Relaxed),
    );
    fmt_u64(
        &mut out,
        "govai_http_errors_total",
        "HTTP responses with status code >= 400.",
        "counter",
        HTTP_ERRORS.load(Ordering::Relaxed),
    );
    fmt_u64(
        &mut out,
        "govai_http_request_duration_nanoseconds_sum",
        "Sum of observed handler latency in nanoseconds (aggregate; divide by count for mean).",
        "counter",
        HTTP_DURATION_SUM_NS.load(Ordering::Relaxed),
    );
    fmt_u64(
        &mut out,
        "govai_http_request_duration_nanoseconds_count",
        "Sample count for govai_http_request_duration_nanoseconds_sum.",
        "counter",
        HTTP_DURATION_COUNT.load(Ordering::Relaxed),
    );

    fmt_u64(
        &mut out,
        "govai_evidence_ingest_accepted_total",
        "Evidence ingest requests accepted (HTTP 200 on POST /evidence).",
        "counter",
        EVIDENCE_INGEST_ACCEPTED.load(Ordering::Relaxed),
    );
    fmt_u64(
        &mut out,
        "govai_evidence_ingest_rejected_total",
        "Evidence ingest requests rejected (non-200 on POST /evidence).",
        "counter",
        EVIDENCE_INGEST_REJECTED.load(Ordering::Relaxed),
    );
    fmt_u64(
        &mut out,
        "govai_compliance_summary_generated_total",
        "Successful compliance summary projections served.",
        "counter",
        COMPLIANCE_SUMMARY.load(Ordering::Relaxed),
    );
    fmt_u64(
        &mut out,
        "govai_ai_decision_trace_events_appended_total",
        "AI decision trace events persisted.",
        "counter",
        AI_TRACE_EVENTS.load(Ordering::Relaxed),
    );

    let r = READINESS_OK.load(Ordering::Relaxed);
    if r >= 0 {
        fmt_i64_gauge(
            &mut out,
            "govai_audit_readiness_ok",
            "1 if the last readiness probe succeeded, else 0 (-1 if never probed).",
            r,
        );
    }
    let h = HEALTH_OK.load(Ordering::Relaxed);
    if h >= 0 {
        fmt_i64_gauge(
            &mut out,
            "govai_audit_health_ok",
            "1 if the last liveness probe succeeded, else 0 (-1 if never probed).",
            h,
        );
    }

    if let Ok(map) = per_route().lock() {
        let mut keys: Vec<&String> = map.keys().collect();
        keys.sort();
        if !keys.is_empty() {
            out.push_str("# HELP govai_http_requests_by_route_total Requests per normalized route template.\n");
            out.push_str("# TYPE govai_http_requests_by_route_total counter\n");
            out.push_str("# HELP govai_http_route_errors_total HTTP errors (>=400) per normalized route.\n");
            out.push_str("# TYPE govai_http_route_errors_total counter\n");
            out.push_str("# HELP govai_http_route_duration_nanoseconds_sum Sum of latency nanoseconds per route.\n");
            out.push_str("# TYPE govai_http_route_duration_nanoseconds_sum counter\n");
            for k in keys {
                let st = map.get(k).expect("key");
                out.push_str("govai_http_requests_by_route_total{route=\"");
                out.push_str(k);
                out.push_str("\"} ");
                out.push_str(&st.count.load(Ordering::Relaxed).to_string());
                out.push('\n');

                out.push_str("govai_http_route_errors_total{route=\"");
                out.push_str(k);
                out.push_str("\"} ");
                out.push_str(&st.errors.load(Ordering::Relaxed).to_string());
                out.push('\n');

                out.push_str("govai_http_route_duration_nanoseconds_sum{route=\"");
                out.push_str(k);
                out.push_str("\"} ");
                out.push_str(&st.sum_ns.load(Ordering::Relaxed).to_string());
                out.push('\n');
            }
        }
    }

    out
}
