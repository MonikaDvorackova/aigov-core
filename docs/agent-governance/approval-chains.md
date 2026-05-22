# Approval chains

Approval chains describe **who must sign off** before an agent or subgraph performs irreversible or high-impact actions. Chains may combine automated policy checks with **human-in-the-loop** steps.

## Design patterns

- **Linear approvals**: ordered reviewers; each step recorded with timestamp and identity.
- **Quorum approvals**: k-of-n agreement for sensitive operations.
- **Time-bounded approvals**: approvals expire to prevent stale authority carrying forward.

## Snapshot fields

Snapshots carry `required_approvals`, `recorded_approvals`, `stale_pending_approvals`, `human_in_loop_required`, and `human_in_loop_observed`. Scoring treats shortfalls, stale items, and missing human confirmation as elevated risk.

## Operational hygiene

Clear pending approvals after rollbacks or cancelled runs. Align ticketing identifiers with approval records so auditors can traverse from decision to ticket to deployment.
