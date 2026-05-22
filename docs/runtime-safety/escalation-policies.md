# Escalation policies

Escalation routes high-risk work from automation to **named humans** with clear SLAs and queue visibility.

## Signals

- **high_risk_sessions_escalated** — volume of sessions routed for review; sustained spikes warrant threshold tuning or staffing.
- **pending_human_review_count** — backlog; non-zero values block dependent automation paths in many designs.
- **sla_breaches_observed** — breaches of agreed first-response or resolution SLAs; each breach should have a post-incident note.
- **median_queue_wait_minutes** — user-visible latency to first human touch; long waits increase residual risk.

## Policy patterns

1. **Tiered routing** — junior reviewers triage; senior reviewers decide overrides.
2. **Time-bounded escalation** — if untouched for N minutes, escalate to the next tier.
3. **Evidence linkage** — link escalation tickets to GovAI `run_id` values when the session produced audit evidence.

This documentation does not change runtime enforcement; operators implement routing in their own incident and review tools.
