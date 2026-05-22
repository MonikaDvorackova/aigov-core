# SLO And SLA Guidance

This page gives operator-facing SLO examples for runtime governance observability. These targets are examples, not product commitments.

## Suggested SLOs

| Objective | Example Target | Source Metric |
|---|---:|---|
| Runtime evaluation availability | 99.5% successful observed evaluations per 30 days | `runtime_evaluations_total` |
| Runtime evaluation latency | 95% under 250 ms per 24 hours | `runtime_evaluation_latency_p95_ms` |
| Audit trace correlation | 99% of completed evaluations include `audit_trace_id` | `audit_trace_correlated_events_total` |
| Governance incident response | Critical incidents triaged within 30 minutes | `governance_incidents_total` |
| BLOCKED verdict visibility | 100% of BLOCKED verdict spikes reviewed daily | `runtime_blocked_verdict_rate` |

## SLA Boundary

The observability layer is a measurement aid. Customer-facing SLAs should be based on the hosted or self-hosted service contract, deployment topology, and support agreement. Do not treat local sample metrics as contractual production data.

## Error Budget Review

When an SLO is missed:

1. Confirm that events include `run_id`, `tenant_id`, `policy_id`, and `audit_trace_id`.
2. Check whether the same issue appears in audit exports.
3. Classify the issue using [`incident-taxonomy.json`](../../observability/incident-taxonomy.json).
4. Record follow-up in the incident report and link the audit trace.
