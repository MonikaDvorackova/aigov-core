# Human oversight

Human oversight ensures that **high-impact** or **ambiguous** decisions receive review by accountable operators before irreversible effects occur.

## Coverage and attribution

- **Coverage** — the fraction of high-risk sessions that received a human decision within the observation window.
- **Attribution** — each decision should record actor identity, role, and rationale pointers suitable for audit export.
- **Dual control** — sensitive operations (for example production overrides) should require two independent approvers where policy demands it.

## Supervision capacity

`active_supervisors_count` reflects how many distinct supervisors were available for escalation. Sustained operation with fewer than two supervisors during peak risk windows should trigger operational review.

## Relation to GovAI evidence

Human approvals captured in GovAI runs remain the **authoritative** promotion gate for that workflow. Runtime safety snapshots summarise **parallel** operational telemetry; they do not replace audit evidence.
