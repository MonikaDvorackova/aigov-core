# Release checklist

## Purpose

Provide a **repeatable, auditable** sequence maintainers follow before tagging or promoting a GovAI release so governance gates, documentation, and operator communications stay aligned.

## Policy

- A release candidate (RC) must pass **automated** checks in [release-runbook.md](release-runbook.md) before tagging.
- **Exactly one** materially new or updated audit report under `docs/reports/` applies when the change set is governance work; documentation-only release prep may reference existing reports if maintainers agree.
- Security-sensitive fixes follow [security-release-process.md](security-release-process.md) in addition to this checklist.

## Maintainer actions

- [ ] Confirm **CHANGELOG.md** **Unreleased** is accurate; move entries into **`[X.Y.Z]`** with date.
- [ ] Run `make release-readiness-check` on the candidate commit (includes `gate`, `validate-changelog`, and `release-readiness-report`).
- [ ] Run `cargo test --manifest-path rust/Cargo.toml` and `cd python && python -m pytest` when Rust or Python code changed.
- [ ] Run `make enterprise-readiness-check` when operational defaults, packaging, or interchange surfaces changed.
- [ ] Optionally build local artefacts: `cd python && python -m build` and `cd rust && cargo package --no-verify`.
- [ ] Fill release notes from [release-notes-template.md](release-notes-template.md) or `make generate-release-notes VERSION=X.Y.Z OUT=release-notes.md`; call out **compatibility** and **deprecations** per [compatibility-policy.md](compatibility-policy.md) and [deprecation-policy.md](deprecation-policy.md).
- [ ] Create signed tag `vX.Y.Z` on the promoted commit; push tags per [release-runbook.md](release-runbook.md).
- [ ] Publish GitHub Release (or distribution channel) with the same body as internal notes.

## Contributor expectations

- Land user-visible changes with **CHANGELOG** entries under **Unreleased** when maintainers request it in review.
- Surface **risk** and **rollback** in PR text when checklist items might fail in production.

## Failure modes

- **Missing gate headings** in `docs/reports/*.md` fail CI — mitigated by `make gate` before tag.
- **Version drift** between Rust, Python, and CHANGELOG — mitigated by `make validate-changelog`.
- **Silent semver violations** — mitigated by maintainer review against [versioning-policy.md](versioning-policy.md).
