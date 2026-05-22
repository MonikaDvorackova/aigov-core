# Evidence flow observability

Evidence flow signals describe **observable behaviour** of evidence ingest and verdict surfaces during a snapshot window. They are not part of the ledger; they are operator-observed summaries useful for trend analysis and SLA-style narratives outside GovAI.

## Signals

| Signal | Type | Notes |
|--------|------|-------|
| `evidence_arrival_latency_p95_seconds` | non-negative integer | P95 latency between evidence emission and acknowledged ingest, measured externally. |
| `evidence_arrival_success_rate_percent` | integer in `[0, 100]` | Ratio of accepted evidence submissions vs total submissions observed in the snapshot window. |
| `submissions_observed` | non-negative integer | Sample size of evidence submissions captured during the window. |
| `compliance_summary_decision_distribution` | object | Counts for `valid`, `invalid`, and `blocked` verdicts emitted during the window. |

## Scoring contribution

Evidence flow contributes to the aggregate health score by weight defined in [observability-manifest.json](observability-manifest.json) (`score_weights.evidence_flow`). The scoring rules in [`scripts/operational_health_score.py`](../../scripts/operational_health_score.py) reduce the sub-score for high latency, low success rate, and elevated non-`valid` decision ratios.

## Non-claims

- These signals are an **operator-side summary**; the **authoritative** verdict for any run remains `GET /compliance-summary?run_id=...` against the hosted or self-hosted audit service.
- They do **not** introduce new verdict semantics or change advisory vs enforcement boundaries described in [`docs/governance/runtime_integration.md`](../governance/runtime_integration.md).

## Cross-references

- Snapshot schema: [diagnostic-snapshots.md](diagnostic-snapshots.md)
- Risk-level derivation: [operational-risk.md](operational-risk.md)
- Telemetry boundaries: [telemetry-boundaries.md](telemetry-boundaries.md)
