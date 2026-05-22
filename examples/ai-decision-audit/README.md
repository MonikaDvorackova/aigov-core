# AI decision flight recorder (multi-agent audit) examples

These examples call the **real** management API routes merged under the assessments router (same base URL as tenant console). Traces are stored **append-only** in Postgres (`govai_ai_decision_trace_events`).

## Prerequisites

- Team must be **ledger-bound** (`POST /api/tenant-console/ledger-binding`) or traces return `400 LEDGER_BINDING_REQUIRED`.
- Caller needs **`ai_decision_trace_write`** to create/append and **`ai_decision_trace_read`** to read/export/list.
- Environment:
  - `GOVAI_BASE_URL` — e.g. `http://127.0.0.1:8088`
  - `GOVAI_ACCESS_TOKEN` — Supabase JWT (same as tenant console smoke)
  - `GOVAI_TEAM_ID` — UUID sent as `x-govai-team-id`

## Run

```bash
python3 examples/ai-decision-audit/run-scenarios.py
```

The script runs multiple scenarios (hash chain + integrity, delegated multi-agent, tool + explainability, blocked policy, human gate with approver fields, invalid delegation DAG, verdict mismatch rejection), validates export JSON (`trace_version: 2` with `trace_integrity` and verdict derivation fields), and checks `GET /api/tenant-console/snapshot` includes `ai_decision_audit` (**schema v3**).

## API surface (implemented)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/ai-decision-traces` | Create `trace_started` (once per `run_id` + ledger tenant) |
| `POST` | `/api/ai-decision-traces/{run_id}/events` | Append `delegation`, `tool_call`, `step`, `policy_eval`, `human_gate`, `completed` |
| `GET` | `/api/ai-decision-traces/{run_id}` | Raw events + folded `export` preview |
| `GET` | `/api/ai-decision-traces/{run_id}/export` | Machine-readable export (`trace_version: 2`, integrity + DAG + verdicts) |
| `GET` | `/api/ai-decision-traces/recent?limit=` | Recent run summaries for the bound ledger tenant |

## Relationship to compliance summary

Immutable **ledger** verdict for a run is only authoritative from **`GET /compliance-summary`**. The export document’s `relation_to_compliance_summary` field states this explicitly; optional `compliance_summary_run_id` in `trace_started` links identifiers when operators align them.
