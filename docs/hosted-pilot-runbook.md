# Hosted pilot runbook (operator + customer)

This runbook makes the hosted-pilot path repeatable enough for teaching pilots (ČVUT) and for collecting future GitHub Marketplace evidence.

It assumes **hosted pilots with manual or semi-automated onboarding**:

- no self-serve signup yet
- the operator must provide a hosted URL and API key

**Stripe billing (optional):** if you charge via Stripe, configure the checklist below and read **[billing.md](billing.md)** end-to-end.

---

## Operator prerequisites

- A machine that can run Docker (single VM is enough for a pilot).
- A stable public HTTPS URL that maps to the audit service (your **audit base URL**).
- A Postgres database (for the simplest pilot, use the included `docker-compose.yml`).
  - Plain Postgres providers (for example Railway) are supported; you do not need to manually create `auth` schema or `auth.users`.

Reference: `docs/hosted-backend-deployment.md`.

### Stripe operator checklist (when billing is enabled)

- **`GOVAI_STRIPE_SECRET_KEY`** — Stripe secret key (test or live) for Checkout, portal, invoices, and metered usage API calls.
- **`GOVAI_STRIPE_WEBHOOK_SECRET`** — signing secret from the Stripe Dashboard (or `stripe listen`); required for **`POST /stripe/webhook`**.
- **Webhook URL** — `https://<audit-host>/stripe/webhook` with the event types listed in **[billing.md](billing.md)**.
- **Price IDs ↔ billing units** — set `GOVAI_STRIPE_PRICE_*` env vars (per unit) as documented in **[billing.md](billing.md)** so subscription line items map to GovAI units.
- **`GOVAI_BILLING_ENFORCEMENT`** — `off` (default) or `on` (`1` / `true` / `yes` / `on`) to gate billable hosted routes on an active/trialing subscription row.

Full behaviour, endpoints, and limitations: **[billing.md](billing.md)**.

---

## Hosted audit endpoint (`audit.govbase.dev`)

For the hosted pilot environment, the audit service is exposed as a **public HTTPS origin**:

- **Correct `GOVAI_AUDIT_BASE_URL`**: `https://audit.govbase.dev`
- **Origin-only**: it must point to the audit service origin and be usable as-is.
  - Do **not** point it to a dashboard or login page.
  - Do **not** include path prefixes like `/api` or `/v1`.

This base URL must serve the audit service endpoints directly, e.g.:

- `GET /health`
- `GET /status`
- `GET /compliance-summary?run_id=...`
- `POST /evidence`

Setup details: `docs/hosted-audit-subdomain.md`.

---

## Start hosted backend (minimal pilot: Docker Compose)

From the repo root:

```bash
docker compose up -d --build
curl -sS http://127.0.0.1:8088/health
curl -sS http://127.0.0.1:8088/status
```

If you are running this on a VM, ensure inbound access to port `8088` (or put it behind an HTTPS reverse proxy and expose `443`).

---

## Provision `base_url` (operator)

Pilot users need the **public** audit API base URL:

- Example: `https://audit.govbase.dev`
- Must route to the audit service and allow:
  - `POST /evidence`
  - `GET /compliance-summary?run_id=...`
  - `GET /health`
  - `GET /status`

If you are using the Docker Compose quickstart, set `GOVAI_BASE_URL` in `docker-compose.yml` so `GET /status` reports the canonical URL.

---

## Provision API key (operator)

In hosted mode, hosted pilots **MUST** enable authentication and tenant isolation by setting **`GOVAI_API_KEYS_JSON`** on the server. This is a JSON object mapping **raw API key string → tenant id** (the tenant id selects the per-tenant ledger file). **Dev mode without API keys is not suitable for pilots**.

- For local pilot setups, you can use: `GOVAI_API_KEYS_JSON='{"test-key":"default"}'`

- **Support contact**: `support@govbase.dev`

Minimal approach:

1) Generate a bearer token (example):

```bash
python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
```

2) Configure the audit service with that token mapped to a tenant id:

- In Compose: set `GOVAI_API_KEYS_JSON='{"<token>":"<tenant_id>"}'` under `govai-audit.environment` (escape quotes as needed for your shell).
- In a hosted deployment: set a single JSON object, e.g. `GOVAI_API_KEYS_JSON='{"<token1>":"tenant-a","<token2>":"tenant-b"}'`.

3) Distribute one token to the pilot user as `GOVAI_API_KEY`.

**Note:** `X-GovAI-Project` / client `GOVAI_PROJECT` do **not** determine the ledger tenant; they are optional metadata (for example metering). Ledger isolation follows the API key mapping only.

Expected failure if not configured correctly:

- `govai run ...` or `govai check ...` returns an auth error (typically HTTP 401/403).

---

## Generate `run_id` (pilot user)

Pilot users generate a UUID and reuse it for:

- evidence submission
- `govai check`
- export

```bash
export GOVAI_RUN_ID="$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"
echo "$GOVAI_RUN_ID"
```

---

## Run deterministic demo (pilot user) to reach `BLOCKED` then `VALID`

This is the canonical proof that the hosted backend + key work.

```bash
python -m pip install --upgrade pip
python -m pip install "aigov-py==0.2.1"

export GOVAI_AUDIT_BASE_URL="https://audit.govbase.dev"
export GOVAI_API_KEY="YOUR_API_KEY"

export GOVAI_DEMO_RUN_ID="$GOVAI_RUN_ID"
govai run demo-deterministic
```

Expected:

- first verdict: `BLOCKED` with an explanation reported via `missing_evidence` and/or `blocked_reasons`
- later verdict: `VALID` after the demo appends the remaining evidence for the same `run_id`

Verify explicitly:

```bash
govai check --run-id "$GOVAI_RUN_ID"
```

---

## Configure GitHub Actions variables/secrets (pilot repo)

In the pilot user’s GitHub repo:

**Settings → Secrets and variables → Actions**

- Variable `GOVAI_AUDIT_BASE_URL` = `https://audit.govbase.dev`
- Variable `GOVAI_RUN_ID` = `<the same run id used above>`
- Secret `GOVAI_API_KEY` = `<the bearer token>`

Then use the artefact-bound gate from `README.md` / `docs/github-action.md`. Optional manual smoke lives in `.github/workflows/govai-smoke.yml` (**not** a production digest gate).

Expected:

- missing any of the above → fail-fast CI with an actionable error
- verdict `BLOCKED` / `INVALID` → CI fails
- verdict `VALID` → CI passes

---

## Export audit JSON (pilot user)

```bash
govai export-run --run-id "$GOVAI_RUN_ID" > "govai-export-${GOVAI_RUN_ID}.json"
ls -la "govai-export-${GOVAI_RUN_ID}.json"
```

Archive this JSON with the build artifacts or attach it to the pilot report.

---

## Capture terminal output (for future Marketplace evidence)

Capture the onboarding session (example):

```bash
mkdir -p govai-evidence
script -q "govai-evidence/onboarding-${GOVAI_RUN_ID}.typescript" <<'SH'
set -e
govai run demo-deterministic
govai check --run-id "$GOVAI_RUN_ID"
govai export-run --run-id "$GOVAI_RUN_ID" > "govai-evidence/export-${GOVAI_RUN_ID}.json"
SH
```

Collect:

- terminal log showing `BLOCKED` then `VALID`
- CI log showing strict failure on non-`VALID` (and success on `VALID`)
- exported JSON

---

## Version tag policy

- Use `@v1` for stable GitHub Action examples once the hosted-pilot evidence is repeatable.
- Use `@v1.0.0` for immutable releases (do not move).
- **Do not cut or advertise tags publicly until you have clean hosted-pilot evidence** (captured output + exported JSON + CI logs).

---

## Troubleshooting (common, pilot-focused)

- **CI fails immediately: Missing required input: base_url**
  - Root cause: `GOVAI_AUDIT_BASE_URL` variable not set or not passed.
  - Fix: set the variable in GitHub Actions and ensure the workflow passes it to the action.

- **CI fails immediately: Missing required input: api_key**
  - Root cause: `GOVAI_API_KEY` secret not set or not passed.
  - Fix: set the secret and pass it to the action.

- **GovAI check failed (cannot fetch verdict)**
  - Root cause: invalid URL, auth rejected, or server not reachable.
  - Fix: curl `GET /health` and `GET /status`; verify the bearer token is a key in `GOVAI_API_KEYS_JSON` on the server.

- **Onboarding demo never reaches `VALID`**
  - Root cause: server policy differs from what the demo expects, or evidence submission is failing.
  - Fix: inspect server logs; confirm the demo’s evidence `POST /evidence` calls are accepted (no 4xx).

