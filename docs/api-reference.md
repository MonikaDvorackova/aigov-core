# HTTP API reference

This page summarizes the **public audit HTTP surface** implemented by the Rust `aigov_audit` binary. **Normative request/response shapes**, stability tags (`x-govai-surface`), and schemas live in [`api/govai-http-v1.openapi.yaml`](../api/govai-http-v1.openapi.yaml). [`ARCHITECTURE.md`](../ARCHITECTURE.md) lists routes alongside repository pointers.

**Hosted audit origin:** Operators configure a public HTTPS base URL (for example `https://audit.govbase.dev`) as `GOVAI_AUDIT_BASE_URL` / `GOVAI_BASE_URL`. That origin is the **live audit API**, not a documentation site.

```docs
preset: api-routes
```

```endpoint
method: GET
path: /compliance-summary
title: Compliance summary (authoritative)
purpose: Returns VALID, INVALID, or BLOCKED for a run_id — same source as govai check.
auth: Bearer API key when GOVAI_API_KEYS* is set
curl: |
  curl -sS "$GOVAI_AUDIT_BASE_URL/compliance-summary?run_id=$GOVAI_RUN_ID" \
    -H "Authorization: Bearer $GOVAI_API_KEY"
response: |
  {"verdict":"VALID","missing_evidence":[],"blocked_reasons":[]}
```

```try-api
title: Try compliance summary
method: GET
path: /compliance-summary?run_id=$GOVAI_RUN_ID
curl: |
  curl -sS "$GOVAI_AUDIT_BASE_URL/compliance-summary?run_id=$GOVAI_RUN_ID" \
    -H "Authorization: Bearer $GOVAI_API_KEY"
auth: Bearer API key
purpose: Authoritative promotion verdict for CI gates.
```

## Authentication

### Audit API keys (ledger tenant)

When API keys are enabled, gated ledger routes expect:

```http
Authorization: Bearer <api_key>
```

- **Hosted / multi-tenant:** configure `GOVAI_API_KEYS_JSON` so each secret maps to a **tenant id** (ledger isolation).
- **Dev / simple:** `GOVAI_API_KEYS` (comma-separated) may be used for local setups.
- **Optional metadata:** `X-GovAI-Project` is an **optional** usage/billing label. It **does not** select the ledger tenant (see OpenAPI description and [`docs/trust-model.md`](trust-model.md)).

### Enterprise JWT (dashboard / assessments)

Routes under `GET /api/me`, `POST /api/assessments`, and `/api/compliance-workflow*` use `Authorization: Bearer <JWT>` with operator-configured JWKS (issuer, audience, and signing keys). These are **separate** from audit API keys. Details: [`ARCHITECTURE.md`](../ARCHITECTURE.md) and OpenAPI `Enterprise` operations.

## Core metadata (usually unauthenticated)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Service banner: `ok`, `service` (`govai`), `version`. **Internal** diagnostic; not required for integrations (OpenAPI). |
| GET | `/health` | **Liveness:** returns minimal JSON such as `{"ok": true}`. Does **not** query Postgres; use `/ready` for dependency health. |
| GET | `/status` | **Stable:** `policy_version`, `environment`, optional `base_url`, runtime governance diagnostics. Not a substitute for `/ready`. |
| GET | `/pricing` | **Stable:** plans and usage units (no payment capture on this route). |

## Readiness

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/ready` | **Operational readiness:** Postgres connectivity, migration markers, ledger writability, tenant-scoped probe. Returns **503** with structured JSON when not ready. OpenAPI classifies this as **`internal`** (operational), but operators should treat it as the **authoritative readiness** probe. |

## Ledger and compliance (authenticated when keys enabled)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/evidence` | Append one `EvidenceEvent`; policy gate; append to hash-chained log. |
| GET | `/usage` | Usage and limits (`metering` off/on shapes). |
| GET | `/verify` | Full-chain integrity check. |
| GET | `/verify-immutable` | Immutable verification variant (see server implementation). |
| GET | `/verify-log` | Compact chain check: `{"ok": true}` or `{"ok": false, "error": …}`. |
| GET | `/bundle?run_id=…` | Bundle document (`schema_version` `aigov.bundle.v1`). |
| GET | `/bundle-hash?run_id=…` | Canonical bundle hash material including **`events_content_sha256`** for CI digest gates. |
| GET | `/compliance-summary?run_id=…` | **Authoritative verdict** projection for the run (`VALID` / `INVALID` / `BLOCKED`). **Required** query param `run_id`. Same semantic source as `govai check`. |
| GET | `/api/export/:run_id` | Machine-readable audit export (`aigov.audit_export.v1`). Used by `govai verify-evidence-pack` optional cross-check. |

**Caching:** Do not cache `GET /compliance-summary` behind generic shared HTTP caches unless you fully understand verdict evolution as new evidence appends.

## Billing (Stripe; authenticated)

Implemented routes (Bearer API key; tenant from key mapping). Shapes are in OpenAPI under `CoreBilling` where listed:

| Method | Path | Summary |
|--------|------|---------|
| GET | `/billing/status` | Billing snapshot for the tenant. |
| POST | `/billing/checkout-session` | Create Checkout session (`success_url`, `cancel_url` required). |
| POST | `/billing/report-usage` | Report metered usage (`billing_unit` optional). |
| POST | `/billing/portal-session` | Billing portal (`return_url` required). |
| GET | `/billing/invoices` | List recent invoices. |
| GET | `/billing/reconciliation` | Usage reconciliation (`from`, `to` query params). |

The server also exposes **`GET /billing/usage-summary`** (usage summary aggregation); see `rust/src/govai_api.rs` and operator docs in [`billing.md`](billing.md) / [`hosted-backend-deployment.md`](hosted-backend-deployment.md).

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/stripe/webhook` | Stripe webhook receiver (**unauthenticated** router segment; Stripe signature verification applies). |

## Preview runtime (explicitly prefixed)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/runtime/evaluate` | **Preview** runtime governance evaluation. Documented in OpenAPI as **`internal`** preview; **does not** change `GET /compliance-summary` semantics. Fail-closed defaults unless shadow/dev opt-in via env (see OpenAPI description). |

## Verdicts: `VALID`, `INVALID`, `BLOCKED`

Authoritative definitions and operational meaning: [`trust-model.md`](trust-model.md).

- **`VALID`** — Policy evaluation for the run succeeded; required evidence satisfied under the active `policy_version`.
- **`INVALID`** — Decisive policy rule failed (for example evaluation failed) with enough evidence to evaluate.
- **`BLOCKED`** — Run not yet eligible for `VALID` (missing required evidence and/or approval/promotion prerequisites per projection).

## Common error semantics

Structured errors follow `rust/src/api_error.rs` / OpenAPI **`ApiError`** patterns:

- Top-level **`ok: false`** on error responses where applicable.
- **`error.code`** — stable `SCREAMING_SNAKE_CASE` discriminator.
- **`error.message`** — short human-readable message.
- **`error.hint`** — suggested recovery action.
- **`error.details`** — optional structured payload (for example readiness **`checks`** on `/ready` failures).

Typical HTTP statuses on gated routes: **400** validation/policy, **401** missing/invalid API key, **403** forbidden (for example team not configured under metering), **409** duplicate `event_id`, **429** rate limit / quota, **503** not ready (`/ready`).

## Further reading

- Product index and links: [`index.md`](index.md)
- GitHub Action and digest gate: [`github-action.md`](github-action.md)
- CLI: [`cli-reference.md`](cli-reference.md)
- Customer flows: [`customer-quickstart.md`](customer-quickstart.md)
