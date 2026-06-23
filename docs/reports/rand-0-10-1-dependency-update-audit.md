# Dependabot staging target audit

## Summary

Dependabot dependency update pull requests must target `staging`, not `main`, so dependency changes follow the repository promotion workflow.

## Files changed

| File | Change |
|------|--------|
| `.github/dependabot.yml` | Sets Dependabot target branch to `staging` for Cargo and Python dependency update PRs. |

## Evaluation gate

Status: pass.

Evidence:
- Cargo dependency updates target `staging`.
- Python dependency updates target `staging`.
- Direct dependency update PRs into `main` are avoided.

## Human approval gate

Status: pending maintainer review.

Reviewer: Monika Dvořáčková
