# Event Taxonomy

GovAI runtime observability events are grouped by operator workflow. The taxonomy is intentionally small so dashboards, incident reports, and audit trace correlation stay stable.

## Lifecycle Events

`govai.runtime.evaluation.started` records that a runtime governance evaluation began. Emit once per local evaluation request when telemetry is enabled.

`govai.runtime.evaluation.completed` records completion. Include `latency_ms` and `verdict` when available. The `verdict` field mirrors the authoritative GovAI result and must not introduce a new decision model.

## Policy Context Events

`govai.runtime.policy.missing` records missing policy or governance metadata. Include `diagnostic_code` and `recommended_action` so operators can distinguish missing configuration from customer evidence gaps.

## Audit Trace Events

`govai.runtime.audit_trace.linked` records that runtime telemetry can be joined to an audit trace. Include `audit_trace_id`, `run_id`, `tenant_id`, and `policy_id`.

## Human Review Events

`govai.runtime.operator.override_requested` records that human review is required. It should include `recommended_action` and must not imply approval.

## Incident Events

`govai.runtime.incident.detected` records operator classification of a governance incident. Include `incident_class` from [`../../observability/incident-taxonomy.json`](../../observability/incident-taxonomy.json).

## Severity Guidance

Use `info` for normal lifecycle events, `warning` for degraded observability, `error` for incidents requiring triage, and `critical` for events requiring immediate human approval or customer-impacting response.
