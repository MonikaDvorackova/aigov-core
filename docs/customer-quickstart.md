## Customer and CI quickstart

This page is the **canonical integration overview** for the hosted audit API and the `govai` CLI. For a **step-by-step hosted console** walkthrough (~10 minutes), use [customer-onboarding-10min.md](customer-onboarding-10min.md) (also mirrored under **Help → Getting started** on [govbase.dev](https://govbase.dev/help/getting-started)). For a **local developer** loop with Docker/Rust/Postgres on loopback, use [quickstart-5min.md](quickstart-5min.md).

**Public documentation** for readers is rendered on **govbase.dev** from this `docs/` tree (for example `/docs/quickstart`, `/docs/api-reference`). The canonical prose remains in GitHub so CI link checks and contributors edit one source.

## What is GovAI

GovAI is an **audit-backed decision service**: you append structured evidence for a `run_id`, and the hosted API returns a single authoritative verdict (`VALID` / `INVALID` / `BLOCKED`) from `GET /compliance-summary`. Semantics are defined in [trust-model.md](trust-model.md).

**CI** often calls `govai check` against the same `run_id` so merges or deploys fail unless the server verdict is `VALID`. **Production-style release gates** should use **`govai submit-evidence-pack`** followed by **`govai verify-evidence-pack`** (digest + optional export cross-check) as documented in [github-action.md](github-action.md)—`check` alone does not prove artefact continuity.

Use one value for `GOVAI_RUN_ID` end to end: evidence submission → decision readout (`check` and/or workflow) → `govai export-run`.

**Preview runtime:** `POST /v1/runtime/evaluate` exists as a **preview** namespace (see [api-reference.md](api-reference.md) and OpenAPI). It does **not** replace `GET /compliance-summary` as the authoritative gate for promotion verdicts.

**Billing:** if your operator enables Stripe on the hosted endpoint, see [billing.md](billing.md) for checkout, status, usage reporting, and enforcement.

```docs
preset: evidence-flow
```

```docs
preset: evidence-demo
```

## Prerequisites

- Python 3.10+
- GOVAI_AUDIT_BASE_URL — base URL of your GovAI audit service
- Optional: GOVAI_API_KEY if your endpoint requires a Bearer token

Install pin must match version in python/pyproject.toml for the release you use.

Ledger tenant: which ledger you read/write is determined only by your API key (GOVAI_API_KEYS_JSON on the server). The optional X-GovAI-Project header (and govai --project) is metadata for usage labels and does not isolate ledger data.

## Hosted billing (Stripe)

If you use a hosted GovAI audit endpoint with Stripe, see billing.md for:

- Checkout (POST /billing/checkout-session)
- Billing status (GET /billing/status)
- Usage reporting (POST /billing/report-usage)
- Billing portal (POST /billing/portal-session)
- Invoices (GET /billing/invoices)
- Reconciliation (GET /billing/reconciliation)
- Webhooks and enforcement behavior

Billing identity is always the ledger tenant derived from your API key, not X-GovAI-Project.

## Step by step integration

```steps
title: Hosted CI integration
steps:
  - label: Install CLI
    command: |
      python -m pip install --upgrade pip
      python -m pip install "aigov-py==0.2.1"
      govai --help >/dev/null && echo "GovAI CLI OK"
    explain: Pin must match python/pyproject.toml for your release tag.
  - label: Configure endpoint
    command: |
      export GOVAI_AUDIT_BASE_URL="https://YOUR_GOVAI_AUDIT_SERVICE"
      export GOVAI_API_KEY="YOUR_API_KEY"
    explain: Omit GOVAI_API_KEY only for legacy unauthenticated dev endpoints.
  - label: Create run_id
    command: |
      export GOVAI_RUN_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
      echo "$GOVAI_RUN_ID"
  - label: POST evidence
    command: |
      export EVENT_ID="evt_${GOVAI_RUN_ID}"
      curl -sS "$GOVAI_AUDIT_BASE_URL/evidence" \
        -H "content-type: application/json" \
        -H "authorization: Bearer $GOVAI_API_KEY" \
        -d @event.json
    explain: See full payload example in repository customer-quickstart history or quickstart-5min.md.
  - label: Gate on verdict
    command: govai check --run-id "$GOVAI_RUN_ID"
    expected: "VALID → exit 0; INVALID → exit 2; BLOCKED → exit 3"
```

After only the minimal event, `govai check` usually returns **BLOCKED** until the full promotion sequence is recorded. Export when ready:

```bash
govai export-run --run-id "$GOVAI_RUN_ID" > "govai-export-${GOVAI_RUN_ID}.json"
```

## Expected results

- CLI runs without error
- Evidence endpoint returns 200
- govai check returns a verdict
- export-run produces JSON

## Troubleshooting

govai command not found  
Reinstall CLI and ensure PATH is correct

401 or 403  
Check GOVAI_API_KEY

BLOCKED  
Missing evidence or approval

VALID locally but fails in CI  
Ensure same GOVAI_RUN_ID, API base URL, and API key