# GovAI billing (Stripe + Postgres)

This document describes the **minimal production-safe billing path**: ledger tenant ↔ Stripe customer/subscription, webhooks, Checkout, usage traces, metered reporting, and optional enforcement.

## Tenant ↔ Stripe mapping

- **Ledger `tenant_id`** is the value from **`GOVAI_API_KEYS_JSON`** for the caller’s API key (see [`rust/src/audit_api_key.rs`](../rust/src/audit_api_key.rs)). It is **not** derived from `X-GovAI-Project`.
- **`tenant_billing_accounts`** (migration `0014_tenant_stripe_billing.sql`) stores one row per `tenant_id` with:
  - `stripe_customer_id`, `stripe_subscription_id`, optional `stripe_subscription_item_id`
  - `subscription_status` (Stripe subscription `status`, or `none` if no row / not yet linked)
  - `current_period_start` / `current_period_end` when known from subscription webhooks
  - `billing_invoice_status` (`paid` / `failed`) when `invoice.paid` / `invoice.payment_failed` match a known customer

Rows are created/updated by:

1. **`POST /billing/checkout-session`** — does not insert DB rows by itself; Stripe Checkout creates the customer/subscription.
2. **Stripe webhooks** — `checkout.session.completed` upserts using `client_reference_id` or `metadata.tenant_id`; `customer.subscription.*` upserts using `subscription.metadata.tenant_id` or, if missing, an existing row matched by `stripe_customer_id`.

## Checkout flow

**Endpoint:** `POST /billing/checkout-session` (Bearer API key required; **not** subject to billing enforcement.)

**Body:**

```json
{
  "price_id": "price_…",
  "success_url": "https://…",
  "cancel_url": "https://…"
}
```

`price_id` is **optional**. When omitted, the server uses **`GOVAI_STRIPE_PRICE_PRO`** (or legacy **`GOVAI_STRIPE_PRICE_TEAM`**). If neither is set → **503** `STRIPE_PRICE_NOT_CONFIGURED`.

**Production redirects (govbase.dev):** use absolute URLs such as `https://govbase.dev/billing?checkout=success` and `https://govbase.dev/billing?checkout=cancel`.

**Behavior:**

- Resolves `tenant_id` from the API key mapping.
- Calls Stripe **`/v1/checkout/sessions`** in **subscription** mode with:
  - `client_reference_id` = `tenant_id`
  - `metadata[tenant_id]` and `subscription_data[metadata][tenant_id]` = `tenant_id`
  - `line_items[0][price]` = `price_id`, quantity `1`

**Response:** `{ "ok": true, "tenant_id", "session_id", "checkout_url" }`

**Requires:** `GOVAI_STRIPE_SECRET_KEY` (sk_test… / sk_live…). If missing or empty → **503** with `STRIPE_NOT_CONFIGURED`.

## Webhook lifecycle

**Endpoint:** `POST /stripe/webhook` (unsigned; uses **`Stripe-Signature`** + **`GOVAI_STRIPE_WEBHOOK_SECRET`**.)

**Persistence:** Every verified event is inserted into **`stripe_webhook_events`** (`stripe_event_id` PK). Duplicates return **200** with `"duplicate": true` once processing completed.

**Processing (idempotent side effects):**

| Event | Effect |
|-------|--------|
| `checkout.session.completed` | Upsert `tenant_billing_accounts` with customer + subscription ids; status `incomplete` if subscription id present |
| `customer.subscription.created` / `updated` | Upsert subscription fields, periods, first subscription item id |
| `customer.subscription.deleted` | Set `subscription_status` to `canceled` |
| `invoice.paid` / `invoice.payment_succeeded` | If customer maps to a tenant: set `billing_invoice_status=paid` |
| `invoice.payment_failed` | If customer maps: `billing_invoice_status=failed`, `subscription_status=past_due` |

Events that cannot be mapped (e.g. invoice for an unknown Stripe customer) **do not fail** the webhook — Stripe still receives **200** after persistence.

**Retries:** If processing fails, the handler returns **500** and leaves `processed_at` null so a **retry** can re-run processing. After success, `processed_at` is set.

**Configure in Stripe Dashboard:** point the webhook URL at `https://<host>/stripe/webhook` and select at least the event types above.

## Usage traces and reporting

1. **Traces:** Each successful **`POST /evidence`** appends **`govai_billing_usage_trace`** (`ledger_tenant_id`, `run_id`, `billing_unit`, default `evidence_event`).
2. **Summary:** `GET /billing/usage-summary` — unchanged; aggregates traces for a time window.
3. **Stripe metered push:** `POST /billing/report-usage` (Bearer; optional body `{ "billing_unit": "evidence_event" }`):
   - Resolves the **current billing window**: subscription `current_period_*` from `tenant_billing_accounts` when present, otherwise **UTC month start → now**.
   - Counts traces in that window.
   - Inserts **`billing_usage_reports`** with unique `(tenant_id, billing_unit, period_start, period_end)` — **idempotent** (second call returns `idempotent_hit: true`).
   - If `stripe_subscription_item_id` is set and `GOVAI_STRIPE_SECRET_KEY` is configured, posts a **usage record** (`action=set`) and stores `stripe_usage_record_id`.
   - If no subscription item id, status **`recorded_local`** (quantity stored only).
   - On Stripe API failure: row **`failed`**, structured **502** `STRIPE_USAGE_REPORT_FAILED`.

**Retries and Stripe failures**

- **Safe against duplicate charging:** repeating **`POST /billing/report-usage`** for the same tenant, unit, and billing window hits the same **`billing_usage_reports`** row (**idempotency**); it does **not** create a second row or a second metered push for that period by default.
- **Not automatic recovery:** if the first attempt left the row in **`failed`**, a later retry returns the existing row (**`idempotent_hit: true`**) without automatically re-calling Stripe until you add an explicit operator or product recovery path (for example fixing config and clearing/advancing state). **Idempotency prevents double charge; it does not guarantee automatic completion** after an external Stripe outage or misconfiguration.

## Billing enforcement

**Variable:** `GOVAI_BILLING_ENFORCEMENT` = `off` (default) | `on` (`1`, `true`, `yes`, `on`).

When **on**, gated routes **reject** tenants whose `tenant_billing_accounts.subscription_status` is **not** `active` or `trialing` with **403** `BILLING_INACTIVE`.

**Never enforced on:**

- `GET /health`, `GET /ready` (core router / unauthenticated audit)
- `POST /stripe/webhook`
- `POST /billing/checkout-session`
- `GET /billing/status`

## Billing status and entitlements

**Endpoint:** `GET /billing/status` (Bearer API key).

Returns Stripe ids, `subscription_status`, `commercial_plan` (`free` | `pro` | `enterprise`), `commercial_plan_display`, `can_use_hosted_api` (true when status is `active` or `trialing`), `latest_invoice_status`, mapped `billing_units`, and operator flags:

- `enforcement_enabled` — whether `GOVAI_BILLING_ENFORCEMENT` is on for this deployment
- `pro_list_price_monthly` — authoritative list price (**499** EUR) for UI copy
- `stripe_configured` / `stripe_checkout_configured` — whether Checkout can run without passing `price_id`

`commercial_plan` may still show **Pro** for `past_due` / `unpaid` while `can_use_hosted_api` is false (display vs entitlement).

`GET /usage` (metering off) resolves the same commercial plan from `tenant_billing_accounts` for limit fields.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `GOVAI_STRIPE_SECRET_KEY` | Stripe API secret for Checkout, portal, invoices, usage records |
| `GOVAI_STRIPE_WEBHOOK_SECRET` | Webhook signing secret (`whsec_…`) |
| `GOVAI_STRIPE_PRICE_PRO` | Default Pro subscription Price for Checkout when `price_id` omitted |
| `GOVAI_STRIPE_PRICE_TEAM` | Legacy alias for Pro Price |
| `GOVAI_STRIPE_PRICE_ENTERPRISE` | Maps subscription items to enterprise entitlements |
| `GOVAI_STRIPE_PRICE_*` (metered) | Optional unit prices — see `stripe_billing.rs` |
| `GOVAI_API_KEYS` + `GOVAI_API_KEYS_JSON` | API keys and ledger tenant ids (required for meaningful multi-tenant billing) |
| `GOVAI_BILLING_ENFORCEMENT` | Optional subscription gate on hosted billable routes (`off` default) |
| `NEXT_PUBLIC_GOVAI_API_BASE_URL` | Dashboard `/billing` → Rust API (browser) |

## Local testing with Stripe CLI

1. Run Postgres + migrate (`sqlx migrate` / `GOVAI_AUTO_MIGRATE` / your deploy process).
2. Export `GOVAI_STRIPE_WEBHOOK_SECRET` from `stripe listen --forward-to localhost:8088/stripe/webhook`.
3. Trigger test events: `stripe trigger customer.subscription.updated` (extend payload JSON in Dashboard **Send test webhook** to include `metadata.tenant_id` matching a key in `GOVAI_API_KEYS_JSON`).
4. Complete Checkout in test mode and confirm `tenant_billing_accounts` updates.

## Known limitations

- **One** metered path: usage records use the **first** subscription item id captured from webhook payloads; complex multi-item subscriptions need operator alignment.
- **No** hosted billing UI, proration, tax, or dunning automation beyond webhook state updates.
- **Team** tables from migration `0012` (`team_billing`, `team_subscriptions`) are **not** wired into this path; this implementation uses **ledger `tenant_id`** (`tenant_billing_accounts`) only.
- Checkout and usage APIs call Stripe over the public network; failures return structured JSON errors.

## Related code

- `rust/src/stripe_billing.rs` — DB + Stripe HTTP helpers
- `rust/src/stripe_webhook.rs` — verify + persist + dispatch
- `rust/migrations/0014_tenant_stripe_billing.sql` — schema
