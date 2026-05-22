# Policy coverage

Policy coverage measures how completely registered policies are **reviewed** and **enforced in CI** relative to the registered inventory. It is a portfolio signal for governance planning, not a substitute for hosted audit verdicts.

## Inputs

Structured snapshots include `policy_inventory` with:

- `registered_policies_count` — modules or packs tracked as in scope.
- `reviewed_policies_count` — versions that completed a documented review.
- `enforced_in_ci_count` — policies wired into compliance-summary or equivalent CI gates.

## Score

The offline scorer (`scripts/policy_coverage_score.py`) blends reviewed ratio and CI enforcement ratio into a single **policy_coverage_score** (0–100). Operators should treat large jumps as triggers for documentation and process review, not as automatic enforcement changes.

## Related

- [`control-plane-reporting.md`](control-plane-reporting.md) for artefact contracts.
- [`governance-non-goals.md`](governance-non-goals.md) for explicit exclusions.
