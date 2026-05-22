# Sample Runtime Governance Incident Report

## Summary

Local sample incident `governance_policy_gap` was detected for `run-local-phase17-002`.

## Correlation

- `run_id`: `run-local-phase17-002`
- `tenant_id`: `tenant-local-demo`
- `policy_id`: `policy.runtime.eu-ai-act-basic`
- `audit_trace_id`: `audit-trace-local-002`

## Classification

- Incident class: `governance_policy_gap`
- Severity: `error`
- Source event: `govai.runtime.incident.detected`

## Triage Notes

The operator should open the linked audit trace before escalating. If the audit trace confirms missing policy context, the policy owner should restore or attach the expected governance metadata. If the audit trace is unavailable, reclassify as `audit_trace_gap`.

## Operator Action

1. Confirm event correlation fields are present.
2. Review the matching audit trace export.
3. Identify whether this is telemetry-only or customer-impacting.
4. Record the owner and remediation status.

## Closure Criteria

Close only after the audit trace is linked, policy context is confirmed, and dashboard incident count returns to baseline.
