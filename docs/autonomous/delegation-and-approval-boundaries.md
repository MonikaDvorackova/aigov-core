# Delegation and approval boundaries

## Delegation

[`../../autonomous/delegation-boundaries.json`](../../autonomous/delegation-boundaries.json) lists:

- **Allowed edges** — `from_role`, `to_role`, `capability_class`, and whether an evidence pack is required for the hand-off.
- **Forbidden edges** — structural anti-patterns (for example executors re-delegating upward) with explicit `reason` strings for audit trails.

Operators should map `capability_class` values to concrete tool policies in their runtime; the JSON bundle stays transportable and small.

## Approval

[`../../autonomous/approval-boundaries.json`](../../autonomous/approval-boundaries.json) defines:

- `human_approval_required_when` — stable taxonomy labels for high-risk classes.
- `delegated_approval_allowed` — set to `false` in the reference bundle to require human or governance-officer approval for promotion-style decisions.

These labels **do not** alter GovAI verdict strings; they guide human process design and offline checks.
