# GovAI Functions 2.0

> [!summary]
> Read-only flight-recorder APIs that package decision intelligence for operators, counsel, and executives — without replacing the immutable ledger verdict from `compliance-summary`.

## Summary

GovAI Functions 2.0 extends the **append-only** AI decision flight recorder (Postgres-backed trace events with **hash-chain** integrity) with richer `event_type` values, a structured `govai_functions_v2` rollup inside trace **export**, and HTTP read APIs for packaged decision intelligence.

> [!compliance]
> **`GET /compliance-summary`** remains the **only authoritative immutable-ledger verdict** for a run. Functions 2.0 explains and packages flight-recorder evidence; it does **not** replace ledger promotion or export semantics.

> [!why]
> Teams need more than a single verdict: they need operational rollups for engineering, executive briefs for leadership, legal indexes for counsel, and deterministic scorecards for readiness — all tied back to the same `run_id` and hash chain.

> [!gives]
> | Capability | Description |
> |------------|-------------|
> | Extended flight events | Approvals, appeals, incidents, remediation, monitoring, seal metadata, legal refs, certification marks, business impact, executive briefs |
> | Trace export rollup | `govai_functions_v2` embedded in trace export for a `run_id` |
> | Read APIs | Flight pack, executive summary, legal evidence manifest, governance scorecard |

> [!when]
> | Endpoint | Use when |
> |----------|----------|
> | `.../flight-pack` | You need the **full** operational picture for engineering or audit review. |
> | `.../executive-summary` | You need a **short** leadership view with ledger verdict pointer and integrity status. |
> | `.../legal-evidence-manifest` | You need **indexed legal evidence references** for counsel or regulatory packs. |
> | `.../governance-scorecard` | You need a **deterministic readiness score** from telemetry (not a substitute for compliance-summary). |

```flow
preset: verdict
```

```docs
preset: api-routes
```

## API endpoints

```endpoint
method: GET
path: /api/functions/v2/{run_id}/flight-pack
title: Flight pack
purpose: Full operational picture — base trace export plus governance operating system rollup.
auth: Bearer session or enterprise JWT; permission ai_decision_trace_read
```

```endpoint
method: GET
path: /api/functions/v2/{run_id}/executive-summary
title: Executive summary
purpose: Short leadership view — model, compliance-summary ref, integrity, optional executive brief.
auth: Bearer session or enterprise JWT; permission ai_decision_trace_read
```

```endpoint
method: GET
path: /api/functions/v2/{run_id}/legal-evidence-manifest
title: Legal evidence manifest
purpose: Indexed legal evidence references for counsel or regulatory packs.
auth: Bearer session or enterprise JWT; permission ai_decision_trace_read
```

```endpoint
method: GET
path: /api/functions/v2/{run_id}/governance-scorecard
title: Governance scorecard
purpose: Deterministic readiness score from telemetry (not a substitute for compliance-summary).
auth: Bearer session or enterprise JWT; permission ai_decision_trace_read
```

## Authentication and permissions

> [!summary]
> Enterprise read routes use session or enterprise JWT — separate from audit API keys used for evidence ingestion and `compliance-summary`.

Enterprise read routes require:

- `Authorization: Bearer <token>` — dashboard session bearer or compatible enterprise JWT
- Optional `x-govai-team-id` when your deployment uses team scope
- Permission **`ai_decision_trace_read`**

These routes are **separate** from audit API keys used for `POST /evidence` and `GET /compliance-summary` with `GOVAI_API_KEY`.

## Try this locally

```try
title: Validate and gate Functions 2.0 packs
mode: local
what: Run the offline pack validator and the repo gate before promoting schema or sample packs.
next: /docs/quickstart
tabs:
  - label: validate
    command: python3 scripts/validate_govai_functions_v2_pack.py --strict examples/govai-functions-2/sample-flight-pack.v1.json
    expected: validate_govai_functions_v2_pack: OK
  - label: make
    command: make functions-v2-check
    expected: functions-v2-check passed
  - label: Python
    command: python3 -c "import json; print('govai_functions_v2 pack gate ready')"
    expected: govai_functions_v2 pack gate ready
  - label: JavaScript
    command: node -e "console.log('govai_functions_v2 pack gate ready')"
    expected: govai_functions_v2 pack gate ready
```

## Example API request

```try-api
title: Fetch executive summary for a run
method: GET
path: /api/functions/v2/{run_id}/executive-summary
auth: Bearer session or enterprise JWT; ai_decision_trace_read
purpose: Leadership-facing rollup with compliance-summary reference and integrity status.
label: Example request (not a live call)
curl: |
  export GOVAI_AUDIT_BASE_URL=https://audit.example.com
  export GOVAI_BEARER_TOKEN=your_session_bearer
  export GOVAI_RUN_ID=your_run_id

  curl -sS "$GOVAI_AUDIT_BASE_URL/api/functions/v2/$GOVAI_RUN_ID/executive-summary" \
    -H "Authorization: Bearer $GOVAI_BEARER_TOKEN" \
    -H "Accept: application/json"
response: |
  {
    "run_id": "01J...",
    "compliance_summary_ref": { "verdict": "VALID" },
    "integrity": { "chain_ok": true },
    "executive_brief": { "headline": "...", "risk_level": "low" }
  }
```

## Error handling

| Status | Meaning |
|--------|---------|
| `401` / `403` | Missing bearer, invalid token, or insufficient permission |
| `404` | Unknown `run_id` or no trace data for the team scope |
| `400` | Invalid path or query (Rust service returns stable JSON body) |

Event ingestion uses `POST /api/ai-decision-traces/{run_id}/events`. Invalid payloads return **400** with a stable error body from the Rust service.

## Best practices

1. Always gate releases with **`GET /compliance-summary`** for the authoritative verdict (`VALID`, `INVALID`, or `BLOCKED`).
2. Use flight-pack for deep dives; use executive-summary for stakeholder updates.
3. Bind ledger tenant to team before writing traces on hosted deployments.
4. Validate offline packs with `scripts/validate_govai_functions_v2_pack.py` before CI promotion.

## Clients

- **OpenAPI:** `api/govai-http-v1.openapi.yaml` (enterprise tier)
- **Python:** `GovAIClient.get_functions_v2_*` in `python/govai/client.py`
- **TypeScript:** `@govai/functions-sdk` in `typescript-sdk/` (`GovaiFunctionsV2Client` for v2 routes)

## Hosted platform

On **govbase.dev**, the same routes are available on the GovAI audit origin when enterprise authentication is configured.
