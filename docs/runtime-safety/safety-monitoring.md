# Safety monitoring

Safety monitoring covers **continuous** observation of guardrail effectiveness, human queue health, and override drill freshness.

## Dashboards

Operators typically chart:

- Block and intervention counts over time (with attack-volume context).
- Human review latency percentiles and SLA breach counters.
- Export latency for audit slices used in incidents.

## Alerting

Recommended alert types (implementation-specific):

- SLA breach count above zero for more than one interval.
- Pending human review count above a budget for sustained periods.
- Break-glass drill age beyond the organisational maximum.

Phase 21 ships **offline** validators and reporters; live alerting remains operator-owned.
