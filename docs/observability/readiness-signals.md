# Readiness signals

Readiness signals describe whether the **operator-controlled** environment is in a state suitable for handling production traffic. They are recorded as **booleans** in each [operational snapshot](diagnostic-snapshots.md) and consumed by [`scripts/operational_health_score.py`](../../scripts/operational_health_score.py).

## Signals

| Signal | Type | Notes |
|--------|------|-------|
| `audit_ready_endpoint_status` | boolean | Derived from `GET /ready` against the configured audit service base URL. Used as a non-authoritative liveness hint. |
| `migration_state_consistent` | boolean | Indicates the operator-controlled migration runner is in a consistent post-migration state and is not mid-rollout. |
| `policy_pack_load_status` | boolean | Whether the configured policy pack manifest loaded without surfaced validation errors during the snapshot window. |

## Scoring contribution

Readiness contributes to the aggregate health score by weight defined in [observability-manifest.json](observability-manifest.json) (`score_weights.readiness`). Any `false` value subtracts from the sub-score; missing fields are treated as critical readiness gaps and contribute to a `critical` risk level when combined with other failures.

## Optional companion fields

Snapshots may include companion metadata such as `policy_pack_name` (a non-secret label of the configured pack). These fields are advisory only and do not affect the score.

## Non-claims

- Readiness booleans are an **observability summary**; they do not gate ingest or change verdict semantics.
- A `true` readiness signal does not imply legal conformity, ledger correctness, or billing state.

## Cross-references

- Snapshot schema: [diagnostic-snapshots.md](diagnostic-snapshots.md)
- Risk-level derivation: [operational-risk.md](operational-risk.md)
- Telemetry boundaries: [telemetry-boundaries.md](telemetry-boundaries.md)
