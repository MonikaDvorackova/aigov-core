# Security release process

## Purpose

Define how GovAI handles **embargoed** vulnerabilities, coordinated disclosure, patch versioning, and operator communications without leaking exploit detail prematurely.

## Policy

- **Report privately** per [SECURITY.md](../../SECURITY.md); do not open public issues for undisclosed vulnerabilities.
- **Embargo:** details stay in the private security channel until agreed **public disclosure time**; fixes land on a private or restricted branch when your Git hosting supports it, then release as **PATCH** unless the fix unavoidably breaks compatibility (**MAJOR**/**MINOR** with maintainer consensus).
- **CVE / advisory:** publish GitHub Security Advisory or equivalent when ready; reference it in **CHANGELOG** and release notes.
- **Downstream:** credit reporters per their preference; avoid attributing blame to integrators.

## Maintainer actions

- Acknowledge receipt of report within the SLA stated in **SECURITY.md**.
- Develop fix, tests, and release notes under embargo; run full readiness including `make release-readiness-check` on the release branch.
- Coordinate **release date** with reporter when reasonable.
- After public release, merge changelog and docs updates to **main** / **staging** per normal flow.

## Contributor expectations

- Do not post proof-of-concept exploits on public PRs before disclosure.
- Follow maintainer directions on commit message and branch naming during incidents.

## Failure modes

- **Premature disclosure** increases exploit risk — mitigated by private channels and embargo checklist.
- **Missing CVE linkage** hampers enterprise consumption — mitigated by advisory + CHANGELOG cross-links.
