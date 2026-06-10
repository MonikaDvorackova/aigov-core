# Operator diagnostics

Runbook for monitoring GovAI Core in production. Pair with [runtime-observability.md](./runtime-observability.md) and [runtime-operations.md](./runtime-operations.md).

## Health vs ready vs status

- **`/health`** — “Is the process up?” Fail → restart container.
- **`/ready`** — “Can this instance accept evidence?” Fail → remove from load balancer; check DB, migrations, `GOVAI_LEDGER_DIR` permissions. Note: performs a one-off ledger append probe.
- **`/status`** — “What is configured and degraded?” Always HTTP 200 when process is up; use `operational_ready` and `readiness_components` for alerting without flapping liveness.

```bash
govai runtime-diagnostics --base-url http://127.0.0.1:8088
```

## What to monitor

| Signal | Source | Alert when |
|--------|--------|------------|
| Process down | `/health` | Non-200 |
| Not accepting traffic | `/ready` | Non-200 or `ready: false` |
| Config drift | `/status` `configuration` | Unexpected `environment` or `policy_source_kind` |
| DB unavailable | `readiness_components.database_ping` | `false` when DB required |
| Migrations pending | `migration_status` | not `complete` / `not_configured` |
| Ledger not writable | `ledger_writable` | `false` |
| Auth misconfiguration | `api_key_allowlist_count` vs `api_key_tenant_map_count` | Mismatch at startup (server fails in prod) |
| Ingest failures | ops log `evidence_ingest` `outcome=rejected` | Spike vs baseline |
| Invalid API keys | ops log `auth_failure` `INVALID_API_KEY` | Sustained rate |
| Duplicate events | HTTP 409 `DUPLICATE_EVENT_ID` | Unexpected burst (client bug or replay attack) |
| Ledger growth | volume metrics on `GOVAI_LEDGER_DIR` | Capacity threshold |
| Export/replay failures | `govai replay-audit-export`, `verify-audit-export` | Non-zero exit in CI or audits |
| Signing verification | `verify-audit-export` | Failures after export download |

## Non-mutating readiness

Prefer **`/status`** for frequent polling (every 30–60s). Reserve **`/ready`** for deploy gates and load-balancer checks (lower frequency) because of the ledger append probe.

## Failed ingest

Check ops logs for `evidence_ingest` with `outcome=rejected` and HTTP status. Common causes:

- Policy gate rejection (400 with policy error code)
- `DUPLICATE_EVENT_ID` (409) — same `event_id` reused
- `INVALID_API_KEY` (401) — key not in allowlist or tenant map mismatch

## Duplicate events

`DUPLICATE_EVENT_ID` is expected when clients retry with the same `event_id`. Alert if rate is high without a known deployment — may indicate a broken idempotency key generator.

## Invalid API keys

Correlate `auth_failure` logs with `configuration.api_key_allowlist_count`. After key rotation, confirm `GOVAI_API_KEYS` and `GOVAI_API_KEYS_JSON` agree (startup validation in staging/prod).

## Export and replay failures

After backup/restore:

1. `GET /api/export/:run_id` for a known run
2. `govai verify-audit-export` when signatures are used
3. `govai replay-audit-export` — investigate `REPLAY_VERDICT_MISMATCH` or chain errors

## Signing verification failures

Ensure `AIGOV_POLICY_TRUST_ED25519_JSON` is set where verification runs. `/status` reports `signing_trust_configured: true` only when trust JSON is present and non-empty. Verification failures do not imply ledger corruption — may indicate tampered export files or wrong trust keys.

## Evaluation and approval gates (diagnostics context)

- **Evaluation** — missing `evaluation_reported` surfaces as **INVALID** in compliance projection; monitor verdict distribution, not model metrics alone.
- **Human approval** — missing `human_approved` keeps runs **BLOCKED**; alert on approval-gated runs stuck in BLOCKED beyond SLA.

Ledger bytes remain authoritative; diagnostics do not override verdicts.
