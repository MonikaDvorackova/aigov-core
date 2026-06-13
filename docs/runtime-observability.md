# Runtime observability

Operator visibility for self-hosted GovAI Core (`aigov_audit`). This is **not** a commercial dashboard or SaaS control plane.

## HTTP probes

| Endpoint | Purpose | Mutates state? |
|----------|---------|----------------|
| `GET /health` | Liveness — process responds | No |
| `GET /ready` | Readiness — DB, migrations, ledger writable, read-only tenant ledger path | No |
| `GET /status` | Diagnostics — config + component states | No |

Use **liveness** for restart decisions. Use **readiness** before routing traffic. Use **status** for dashboards and incident triage without failing load balancers.

### `/status` fields (safe subset)

- `runtime_version`, `environment`, `policy_version`
- `uptime_seconds`, `started_at_utc`
- `operational_ready` — derived from non-mutating readiness checks
- `configuration` — ledger/database/policy paths (redacted labels), API key **counts** only, `signing_trust_configured`
- `readiness_components` — `database_ping`, `migrations_complete`, `migration_status`, `ledger_writable`, `ledger_tenant_readable`
- `otel` — trace-linking hooks (no vendor SDK in Core)

Never returned: raw API keys, `DATABASE_URL`, private signing seeds, full tenant identifiers, policy JSON bodies.

## Structured logging

Core emits single-line JSON on **stderr** (`channel: govai.ops`). Example lines: [examples/observability/json-ops-log.example.jsonl](../examples/observability/json-ops-log.example.jsonl).

Recommended operator fields (your log agent may add these):

| Field | Usage |
|-------|--------|
| `request_id` | Correlate one HTTP request across log lines |
| `run_id` / `run_id_len` | Tie ingest to compliance/export (length only in ops logs when full id is sensitive) |
| `tenant_scope` | Use `mapped` / `api_key_derived` — avoid raw tenant ids in shared logs |
| `error_code` | Stable codes: `INVALID_API_KEY`, `DUPLICATE_EVENT_ID`, `NOT_READY`, `REPLAY_VERDICT_MISMATCH` |
| `route_key` | Bounded route label from metrics normalization (`POST /evidence`) |

Ship logs to any aggregator (Loki, Elasticsearch, CloudWatch, etc.). No vendor lock-in.

### Replay verification errors

Log `replay_verification_failed` with `error_code` when offline or CLI replay disagrees with export verdict. Operators should alert on sustained `REPLAY_VERDICT_MISMATCH` or `REPLAY_CHAIN_BREAK` after restores.

## Prometheus metrics

`GET /metrics` exposes request latency and evidence ingest counters (when mounted). See [examples/observability/scrape-metrics.example.sh](../examples/observability/scrape-metrics.example.sh).

## OpenTelemetry and trace linking

GovAI Core does **not** bundle an OpenTelemetry SDK. Optional linking:

1. Parse W3C `traceparent` at your agent/gateway ([`python/aigov_py/trace_context.py`](../python/aigov_py/trace_context.py), Rust `trace_context` module).
2. Attach to evidence payload:

```json
{
  "external_trace": {
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "00f067aa0ba902b7",
    "trace_flags": "01",
    "propagation": "w3c_traceparent"
  }
}
```

3. Correlate ledger `run_id` with your trace backend using shared `request_id` / `external_trace.trace_id`.

Your OTel collector remains the system of record for spans; the ledger remains authoritative for governance verdicts.

## Operator CLI

```bash
govai runtime-diagnostics --base-url http://127.0.0.1:8088
govai runtime-diagnostics --json
```

## Limitations

- No built-in alerting rules or SaaS incident UI
- `/ready` is read-only — safe for deploy gates and load-balancer probes at normal polling intervals
- Trace linking is payload convention only — not automatic span creation inside Core
