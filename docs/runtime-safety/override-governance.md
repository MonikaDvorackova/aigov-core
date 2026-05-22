# Override governance

Overrides allow humans to **break glass** when automation would otherwise block legitimate emergency work. Governance minimizes abuse and preserves traceability.

## Readiness signals

- **override_playbook_version_present** — a versioned playbook artifact exists and is discoverable.
- **emergency_break_glass_last_drill_days_ago** — drills prove the path still works after infra changes.
- **audit_trail_export_latency_p95_seconds** — regulators and incident leads must retrieve evidence quickly after an override.
- **rollback_procedure_documented** — after an override, operators restore safe defaults.

## Principles

- Overrides are **rare**, **attributed**, and **time-bounded**.
- Every override generates or references audit evidence suitable for later review.
- Billing and ledger semantics remain unchanged by Phase 21 tooling; overrides are documented at the **policy and operations** layer.
