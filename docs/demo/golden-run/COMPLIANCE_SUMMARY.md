# Compliance summary for the golden run

**Run ID:** `68460594-91c0-4e63-8722-bd4f2f54abe5`

The compliance projection is the HTTP contract **`aigov.compliance_summary.v2`** (`current_state` uses **`aigov.compliance_current_state.v2`**). Specification: [`docs/strong-core-contract-note.md`](../../strong-core-contract-note.md).

**Why there is no `compliance-summary.json` in this folder:** `GET /compliance-summary` is implemented against the append-only ledger (`rust/audit_log.jsonl`). Repository snapshots under `docs/evidence/` are portable artifacts; they are not guaranteed to match the current local ledger, so vendoring a second JSON snapshot would be misleading without a paired log replay.

**Practical use:** for API-accurate JSON, run **`aigov_audit`** with a ledger that contains this run’s events, then call `GET /compliance-summary?run_id=68460594-91c0-4e63-8722-bd4f2f54abe5`. For offline inspection of the same underlying events, use the evidence bundle linked from [`README.md`](./README.md).
