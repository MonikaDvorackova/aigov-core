# GovAI Functions 2.0 examples

This directory holds fixtures for the **GovAI Functions 2.0** decision intelligence layer:

- Append-only AI decision flight recorder extensions (new `event_type` values on `POST /api/ai-decision-traces/{run_id}/events`).
- Read APIs under `GET /api/functions/v2/{run_id}/*` (flight pack, executive summary, legal evidence manifest, governance scorecard).

## Fixture validation

From the repository root:

```bash
python3 scripts/validate_govai_functions_v2_pack.py --strict examples/govai-functions-2/sample-flight-pack.v1.json
```

The same check runs as part of `make oss-diagnostics` / `make enterprise-readiness-check` via `make functions-v2-check`.

## Authoritative verdict

Immutable ledger compliance for a run remains **`GET /compliance-summary`**. Flight recorder exports and Functions 2.0 packs are operational governance telemetry stored in Postgres with hash-chain integrity.
