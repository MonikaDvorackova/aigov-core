# Multi-agent orchestration

Multi-agent orchestration coordinates **specialised workers** under an **orchestrator** while preserving **traceability** across hand-offs.

## Orchestration practices

- **Correlation identifiers**: propagate a single correlation id across every delegation edge so logs and exports line up.
- **Fan-out control**: cap concurrent delegates per orchestrator to limit blast radius.
- **Idempotent hand-offs**: workers should tolerate duplicate deliveries without double-applying side effects.

## Observability alignment

Orchestration telemetry complements Phase 17 operational snapshots: governance snapshots focus on **delegation structure and approvals**, not HTTP latency of the audit service.

## References

Pair this guide with [Agent accountability](agent-accountability.md) for ownership mapping and [Delegation risk management](delegation-risk-management.md) for abuse cases.
