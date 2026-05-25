# GovAI Core runtime API contract (`aigov_audit`)

This document describes the HTTP surface **mounted by the `aigov_audit` binary** in this repository. It is ledger-authoritative: compliance verdicts and exports are derived from append-only evidence in tenant-scoped JSONL ledgers, not from Postgres trace tables or platform workflow state.

Platform-only routes (`/usage`, `/pricing`, enterprise `/api/*` except export path below) may appear in [govai-http-v1.openapi.yaml](../api/govai-http-v1.openapi.yaml) with `x-govai-runtime-mount: platform-only` but are **not** served by `aigov_audit`.

## Mounted routes

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/health` | none | Liveness |
| `GET` | `/status` | none | Policy version and deployment tier |
| `GET` | `/ready` | none | Non-mutating readiness (DB optional, ledger dir, read-only path check) |
| `GET` | `/` | none | Service banner (internal) |
| `POST` | `/evidence` | Bearer | Append one evidence event |
| `GET` | `/compliance-summary` | Bearer | Query: `?run_id=` |
| `GET` | `/compliance-summary/:run_id` | Bearer | Path alias for summary |
| `GET` | `/bundle` | Bearer | Query: `?run_id=` |
| `GET` | `/bundle/:run_id` | Bearer | Path alias |
| `GET` | `/bundle-hash` | Bearer | Query: `?run_id=` |
| `GET` | `/bundle-hash/:run_id` | Bearer | Path alias |
| `GET` | `/api/export/:run_id` | Bearer | `aigov.audit_export.v1` document |
| `GET` | `/verify` | Bearer | Verify tenant ledger hash chain |
| `GET` | `/verify/:run_id` | Bearer | Verify chain; ensure run exists in tenant ledger |

## Authentication and tenant isolation

1. Configure `GOVAI_API_KEYS` (comma-separated bearer allowlist, optional per-key caps `key:limit`).
2. Configure `GOVAI_API_KEYS_JSON` as `{"<api_key>": "<ledger_tenant_id>", ...}`.
3. Every authenticated ledger request sends `Authorization: Bearer <api_key>`.
4. The server resolves **ledger tenant only from the API key** (env map, then optional DB-issued keys when hosted self-service is enabled).
5. If `GOVAI_API_KEYS` is non-empty, **`GOVAI_API_KEYS_JSON` is required** at startup; unknown keys receive HTTP 401.
6. `X-GovAI-Project` may be sent as **metadata**; it does **not** select the ledger file.

Legacy dev single-tenant mode (no allowlist, empty map, no bearer token) may use tenant `"default"`. Do not use that mode for multi-tenant pilots.

## Verdict semantics (`GET /compliance-summary`)

| Verdict | Meaning (ledger projection) |
|---------|------------------------------|
| `VALID` | Required evidence present, evaluation passed, promotion state `promoted` |
| `INVALID` | Evaluation failed |
| `BLOCKED` | Missing evidence, rejected approval/review, or not yet promoted |

Trace-derived or Postgres workflow verdicts are **not** used on this route.

## Export (`GET /api/export/:run_id`)

Returns schema `aigov.audit_export.v1` (see [schemas/aigov.audit_export.v1.schema.json](schemas/aigov.audit_export.v1.schema.json)). Event ordering is deterministic. CI validates example exports against the JSON Schema.

## Readiness (`GET /ready`)

Checks may include:

- `database_ping` / `migrations_complete` (when `DATABASE_URL` is set)
- `ledger_writable` (`GOVAI_LEDGER_DIR` validation)
- `ledger_tenant_readable` (directory + read-only access; **no append probe**)

Repeated `/ready` calls must not grow ledger files or change bundle hashes.

## Examples and CI

- Curl smoke: [examples/basic-runtime-client/](../examples/basic-runtime-client/)
- Python smoke: [examples/python-runtime-client/](../examples/python-runtime-client/)
- Route drift check: `make core-runtime-examples-check`
