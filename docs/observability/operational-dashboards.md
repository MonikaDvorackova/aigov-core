# Operational Dashboards

Dashboard definitions are documented in [`../../observability/dashboard-metrics.json`](../../observability/dashboard-metrics.json). The examples are local and vendor-neutral.

## Core Panels

| Panel | Metric ID | Operator Question |
|---|---|---|
| Runtime evaluations | `runtime_evaluations_total` | Are runtime governance evaluations flowing? |
| BLOCKED verdict rate | `runtime_blocked_verdict_rate` | Are governance blocks increasing for a tenant or policy? |
| Evaluation latency | `runtime_evaluation_latency_p95_ms` | Is runtime governance adding operational latency? |
| Audit correlation | `audit_trace_correlated_events_total` | Can operators join telemetry to audit evidence? |
| Governance incidents | `governance_incidents_total` | What incidents need triage by class and severity? |

## Recommended Filters

Use `tenant_id`, `policy_id`, `run_id`, `severity`, `component`, and `incident_class` as primary dashboard filters. Avoid filters that expose raw prompts, model outputs, or customer data.

## Dashboard Consumption

The sample summary in [`../../examples/observability/sample-dashboard-summary.json`](../../examples/observability/sample-dashboard-summary.json) shows how local tools can consume metric IDs without depending on an external telemetry backend.
