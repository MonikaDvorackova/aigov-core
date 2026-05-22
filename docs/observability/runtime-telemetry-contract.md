# Runtime Telemetry Contract

This contract defines the operational telemetry GovAI operators can emit around runtime governance. It is an observability layer only: it does not change `VALID`, `INVALID`, or `BLOCKED` verdict semantics and does not modify runtime enforcement.

Canonical machine-readable files:

- [`../../observability/runtime-event-schema.json`](../../observability/runtime-event-schema.json)
- [`../../observability/runtime-event-examples.json`](../../observability/runtime-event-examples.json)
- [`../../observability/dashboard-metrics.json`](../../observability/dashboard-metrics.json)
- [`../../observability/incident-taxonomy.json`](../../observability/incident-taxonomy.json)

## Event Names

| Event | Purpose |
|---|---|
| `govai.runtime.evaluation.started` | Runtime governance evaluation began. |
| `govai.runtime.evaluation.completed` | Runtime governance evaluation completed and may report the observed verdict. |
| `govai.runtime.policy.missing` | Required runtime policy context was absent from the request path. |
| `govai.runtime.audit_trace.linked` | Runtime telemetry was linked to a GovAI audit trace. |
| `govai.runtime.operator.override_requested` | Human review or override workflow was requested. |
| `govai.runtime.incident.detected` | Operator tooling classified a runtime governance incident. |

## Required Fields

Every runtime event must include:

- `event_name`
- `event_version`
- `event_time`
- `severity`
- `run_id`
- `tenant_id`
- `policy_id`
- `audit_trace_id`
- `source`
- `message`

The correlation fields are mandatory so operators can join telemetry, audit exports, and incident reports without relying on request payload content.

## Recommended Fields

Recommended fields are optional but should be included when available:

- `component`
- `diagnostic_code`
- `incident_class`
- `latency_ms`
- `recommended_action`
- `verdict`

`verdict` is observational only. It must report the authoritative GovAI verdict returned elsewhere; telemetry must not derive or rewrite compliance outcomes.

## Severity Levels

- `debug`: local diagnostics or low-level operator troubleshooting.
- `info`: expected lifecycle event.
- `warning`: degraded traceability, elevated latency, or non-blocking policy context issue.
- `error`: governance incident requiring operator triage.
- `critical`: human approval, override review, or customer-impacting governance incident.

## Correlation Model

Use `run_id`, `tenant_id`, and `policy_id` on every event. Use `audit_trace_id` to connect runtime activity to evidence exports and audit reports. Dashboard joins should prefer these opaque identifiers over request content.

## Privacy And Minimization

Runtime events must not contain prompts, model outputs, secrets, API keys, personal data, or raw customer payloads. Use opaque IDs, short diagnostic codes, and local operator messages. If a value is not needed for dashboarding, SLO measurement, or incident triage, omit it.
