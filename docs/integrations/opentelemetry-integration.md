# OpenTelemetry tracing integration guide

## Purpose

Help platform teams **correlate GovAI HTTP calls and evidence lifecycle** with existing traces, metrics, and logs—using standard OTLP exporters—without modifying GovAI server internals in this repository.

## Integration overview

OpenTelemetry (OTel) instruments **your services** that call GovAI:

- **Client spans** — wrap `POST /evidence` and `GET /compliance-summary` in spans; attach attributes: `http.url` (sanitized), `http.status_code`, `govai.run_id`, `govai.project` if used.
- **Propagated context** — continue trace context from upstream web requests through batch jobs posting evidence.
- **Exporter** — send OTLP to your collector (Grafana Tempo, Honeycomb, Datadog agent, etc.); this is entirely on the integrator side.

GovAI’s Rust audit service may or may not emit OTel in a given deployment; the integrator guide assumes **client-side** instrumentation first.

## Implementation steps

1. **Enable OTel in your app** — add the OTel SDK for Python/Node/Go per vendor docs; configure `OTEL_EXPORTER_OTLP_ENDPOINT` and auth headers via environment.
2. **Wrap GovAI client calls** — start a span named `govai.post_evidence` / `govai.compliance_summary` around the HTTP client; record exceptions on non-success.
3. **Redaction** — strip bearer tokens from span attributes; never log raw API keys.
4. **Sampling** — for high-volume evidence posts, use head-based or tail-based sampling policies that still retain error traces.
5. **Dashboards** — build panels linking `trace_id` from a failed deployment to the `run_id` attribute and the audit export URL (operator-permitted).

## Validation

- Smoke-test: generate a trace with a dev GovAI URL and confirm spans appear in your backend.
- `python3 scripts/developer_integrations_check.py` for repository documentation completeness.
- Security review: verify no secrets in span attributes (static analysis or manual checklist).

## Failure modes

- **Credential leakage via attributes** — copying full headers into spans. Mitigation: allowlist attributes only.
- **Cardinality explosion** — using high-cardinality labels like raw prompt text as attributes. Mitigation: hash or omit; follow your observability vendor limits.
- **False causality** — spans show HTTP 200 while verdict is `BLOCKED`. Mitigation: add span event or attribute with `govai.verdict` read from the JSON body.
