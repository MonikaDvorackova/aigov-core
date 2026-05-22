# Incident Response

Runtime observability incidents are operational classifications around governance telemetry. They do not change compliance verdict semantics.

## Incident Classification

Use the machine-readable classes in [`../../observability/incident-taxonomy.json`](../../observability/incident-taxonomy.json):

- `governance_policy_gap`
- `audit_trace_gap`
- `runtime_latency_degradation`
- `operator_override_review`

## Triage Steps

1. Identify the event with the highest `severity`.
2. Use `run_id`, `tenant_id`, `policy_id`, and `audit_trace_id` to open the corresponding audit trace or evidence export.
3. Confirm whether the issue is telemetry-only, policy-context related, or customer-impacting.
4. Capture operator action, owner, and current status in the incident report.
5. For `critical` incidents, require human approval before any operational override is treated as resolved.

## Escalation

Escalate to policy owners for `governance_policy_gap`, platform owners for `runtime_latency_degradation`, audit owners for `audit_trace_gap`, and compliance approvers for `operator_override_review`.

## Closure Criteria

An incident is ready to close when the audit trace is linked, operator action is documented, customer impact is assessed, and dashboard signals have returned below the relevant threshold.
