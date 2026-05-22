# Serious incident reporting workflow

[`incident-reporting-workflow.json`](../../conformity/incident-reporting-workflow.json) describes the operator-internal flow used to triage, escalate, and notify competent authorities about events that meet the EU AI Act definition of a serious incident (Article 73).

## Trigger criteria

The artefact lists indicative criteria such as serious harm to health, disruption of critical infrastructure, fundamental-rights violations, and serious damage to property or the environment. Final classification remains with the regulatory owner and counsel.

## Workflow steps

| Step | Intent |
| --- | --- |
| Detect | Capture the event from monitoring, support, or external report. |
| Triage | Apply trigger criteria and decide on classification. |
| Contain | Apply pause, rollback, or guardrail changes; coordinate with deployers. |
| Notify | Prepare and send notification to the competent authority within the required deadline. |
| Report and close | Document root cause, update risk register, and obtain sign-off. |

The `notify` step records indicative deadlines (`default_initial_notification_hours_max`, `shorter_deadline_if_widespread_or_fatal_hours`). The binding timelines are set by Article 73 and the implementing acts; operators should treat the defaults as **minimum awareness markers**, not maximum allowances.

## Evidence attachments

When notifying an authority, providers may attach audit log exports, evidence packs for affected runs, and operational intelligence reports. `evidence_export_hooks` lists the existing GovAI scripts that produce these artefacts.

## Boundaries

GovAI does **not** transmit notifications to authorities; operators handle external communications. Personal data protections still apply to any attached evidence.
