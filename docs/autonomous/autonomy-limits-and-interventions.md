# Autonomy limits and interventions

## Limits

[`../../autonomous/autonomy-limits.json`](../../autonomous/autonomy-limits.json) caps autonomous behaviour:

- Throughput (`max_actions_per_minute`, `max_tool_calls_per_session`).
- Session duration (`max_session_duration_minutes`).
- Concurrency (`max_concurrent_sub_agents`).
- Optional `scope_constraints` strings for operator interpretation.

Tune these per environment; the repository ships **illustrative** numbers for CI-stable validation.

## Interventions

[`../../autonomous/intervention-points.json`](../../autonomous/intervention-points.json) names **intervention points** with:

- `trigger_class` — what signal fires the intervention (operator console, policy engine, autonomy limits, approval match).
- `default_response` — `halt_pending_human`, `escalate_to_governance_officer`, `degrade_to_readonly_executor`, or `pause_and_request_approval`.

Use this catalogue when designing runbooks: each `id` should map to concrete dashboards, webhooks, or on-call procedures in your deployment.
