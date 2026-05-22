# Release checklist

## Purpose

Provide a **repeatable, auditable** sequence maintainers follow before tagging or promoting a GovAI release so governance gates, documentation, and operator communications stay aligned.

## Policy

- A release candidate (RC) must pass **automated** checks in [release-runbook.md](release-runbook.md) before tagging.
- **Exactly one** materially new or updated audit report under `docs/reports/` applies when the change set is phase-style governance work; documentation-only release prep may reference existing reports if maintainers agree.
- Security-sensitive fixes follow [security-release-process.md](security-release-process.md) in addition to this checklist.

## Maintainer actions

- [ ] Confirm **CHANGELOG.md** **Unreleased** is accurate; move entries into **`[X.Y.Z]`** with date.
- [ ] Run `make release-readiness-check` on the candidate commit (includes `release-operations-check`, `gate`, `docs-links-strict`).
- [ ] Run agreed product checks (for example `make enterprise-readiness-check`) when Rust, Python, or operational defaults changed.
- [ ] Fill release notes from [release-notes-template.md](release-notes-template.md); call out **compatibility** and **deprecations** per [compatibility-policy.md](compatibility-policy.md) and [deprecation-policy.md](deprecation-policy.md).
- [ ] Create signed tag `vX.Y.Z` on the promoted commit; push tags per [release-runbook.md](release-runbook.md).
- [ ] Publish GitHub Release (or distribution channel) with the same body as internal notes.

## Contributor expectations

- Land user-visible changes with **CHANGELOG** entries under **Unreleased** when maintainers request it in review.
- Surface **risk** and **rollback** in PR text when checklist items might fail in production.

## Failure modes

- **Skipped link validation** breaks public docs — mitigated by `docs-links-strict` in release readiness.
- **Missing gate headings** in `docs/reports/*.md` fail CI — mitigated by `make gate` before tag.
- **Silent semver violations** — mitigated by maintainer review against [versioning-policy.md](versioning-policy.md).
