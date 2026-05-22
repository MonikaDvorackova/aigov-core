# Runtime health signals

Runtime health describes how the **audit service** and surrounding operator-controlled infrastructure are behaving during a given **window**. It is captured externally — typically by an operator monitoring stack — and recorded in an [operational snapshot](diagnostic-snapshots.md) for offline scoring.

## Signals

| Signal | Type | Notes |
|--------|------|-------|
| `audit_service_uptime_minutes` | non-negative integer | Observed continuous uptime for the snapshot window. Values below 60 minutes drive a higher operational risk weighting. |
| `error_rate_percent` | integer in `[0, 100]` | Operator-visible error rate across audit endpoints (`/evidence`, `/compliance-summary`, `/api/export`, `/verify`). |
| `open_incidents_count` | non-negative integer | Currently open operational incidents tracked outside GovAI. Each open incident reduces the runtime health score. |

## Scoring contribution

Runtime health contributes to the aggregate health score by weight defined in [observability-manifest.json](observability-manifest.json) (`score_weights.runtime_health`). The scoring rules in [`scripts/operational_health_score.py`](../../scripts/operational_health_score.py) reduce the sub-score for elevated error rates, open incidents, and short uptime windows.

## Non-claims

- Runtime health is **not** an authoritative SLA statement. SLAs remain operator-owned and contractual.
- These signals are **observability hints**; they do not change verdict semantics or runtime enforcement.
- The audit service’s own health/readiness probes (`/health`, `/ready`) remain authoritative for ingest gating.

## Cross-references

- Snapshot schema: [diagnostic-snapshots.md](diagnostic-snapshots.md)
- Risk-level derivation: [operational-risk.md](operational-risk.md)
- Telemetry boundaries: [telemetry-boundaries.md](telemetry-boundaries.md)
