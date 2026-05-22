# GovAI governance (platform repository)

This document describes how the **private GovAI platform** repository is governed: who decides what, how to propose changes, and where to escalate security or conduct concerns.

**License:** this tree is **proprietary** ([LICENSE](LICENSE)). The **public open-core runtime** is governed separately in **[govai-core](https://github.com/govbase-dev/govai-core)**.

## Maintainer model

- **Maintainers** merge contributions, cut releases, and keep enforcement and audit guarantees consistent with project goals.
- **Default code ownership** for review routing is defined in **[`.github/CODEOWNERS`](.github/CODEOWNERS)**.
- Day-to-day maintainer expectations (triage, review bar) are expanded in **[`docs/project/maintainer_guide.md`](docs/project/maintainer_guide.md)**.

## Contributor decision process

- **Normal changes** land via pull request into **`staging`** (see **[`docs/project/contributor_workflow.md`](docs/project/contributor_workflow.md)** and the PR template).
- **Promotion to `main`** is via **`staging` → `main`** only, per branch policy enforced in CI.
- **Disagreement on direction** should be resolved in issue discussion first; maintainers make the final call when consensus is not possible.
- **Open-core runtime changes** that belong in the public repository should be proposed in **govai-core**, not assumed to inherit platform repo license terms.

## RFC and design discussion

- Substantial design or breaking behavioural proposals should use **`docs/rfcs/`** patterns where applicable (see **[`docs/rfcs/README.md`](docs/rfcs/README.md)** and the RFC template).
- **Runtime governance, evidence, and verdict semantics** changes require explicit review — call them out in the PR description.

## Release expectations

- Release discipline follows the same branch flow: integrate on **`staging`**, then promote to **`main`** when ready.
- **Core or enforcement-adjacent** changes may require an audit report under **`docs/reports/*.md`** with the standard headings expected by **`scripts/gate_reports.py`** (see contributor workflow).

## Security escalation

- **Do not** file undisclosed vulnerabilities as public issues.
- Follow **[`SECURITY.md`](SECURITY.md)** and GitHub Security Advisories for private reporting.

## Code ownership

- See **[`.github/CODEOWNERS`](.github/CODEOWNERS)** for area ownership defaults.

## Community conduct

- All contributors are expected to follow **[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)** in issues, pull requests, discussions, and official community channels.
