# AIGov Core governance

This document describes how the **AIGov Core** open-source repository is governed.

## Project scope

AIGov Core is the ledger-authoritative audit runtime (`aigov_audit`), integrator SDKs, portable standards tooling, and documentation for self-hosted or embedded audit deployments.

Changes that expand into hosted SaaS, billing, dashboard ACL, or commercial onboarding are out of scope for this repository unless explicitly reclassified by maintainers.

## Maintainer model

- **Maintainers** merge contributions, tag releases, and protect core invariants (append-only ledger, tenant isolation, ledger-authoritative verdicts).
- Default review routing: **[`.github/CODEOWNERS`](.github/CODEOWNERS)**.
- Operating guide: **[`docs/project/maintainer_guide.md`](docs/project/maintainer_guide.md)**.

## Decision process

- Normal changes land via pull request into **`staging`**, then promote to **`main`**.
- Substantial design proposals: **`docs/rfcs/`** when applicable.
- Runtime, evidence, verdict, readiness, or export semantics require explicit call-out in PR descriptions.

## Release expectations

- Integrate on **`staging`**, promote to **`main`** when ready.
- Governance-adjacent changes may require audit reports under **`docs/reports/`** (see **`scripts/gate_reports.py`**).

## Security escalation

Follow **[`SECURITY.md`](SECURITY.md)** — no public issues for undisclosed vulnerabilities.

## Code ownership

See **[`.github/CODEOWNERS`](.github/CODEOWNERS)**.

## Community conduct

All participants follow **[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)**.
