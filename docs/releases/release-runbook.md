# Maintainer release runbook

## Purpose

Give maintainers a **single path** from merge-ready `staging` (or agreed branch) to a published **`vX.Y.Z`** tag and release notes, including commands and rollback posture, without improvising per release.

## Policy

- Releases promote from **`staging`** to **`main`** per [GOVERNANCE.md](../../GOVERNANCE.md); tags are created only on commits that passed the checklist in [release-checklist.md](release-checklist.md).
- **Deterministic scripts first:** `make release-readiness-check` (changelog validation, readiness report, documentation gate) is a mandatory pre-tag step for release-structure hygiene; it does **not** replace service-level tests when code changed.
- **Cadence:** default expectations live in [release-cadence.md](release-cadence.md); emergency exceptions require security process when applicable.

## Maintainer actions

1. **Freeze** the candidate: note SHA, compare `CHANGELOG.md` vs merged PRs.
2. **Validate:** `make release-readiness-check` from repo root.
3. **Tag:** `git tag -a vX.Y.Z -m "GovAI vX.Y.Z"` on the agreed commit; `git push origin vX.Y.Z`.
4. **Publish:** GitHub Release with notes from [release-notes-template.md](release-notes-template.md).
5. **Post-release:** merge any version bump follow-ups (for example lockfile or manifest sync) as a fast-follow **PATCH** if required by automation.

## Contributor expectations

- Do not create release tags from unreviewed branches.
- Provide verification commands in PRs touching release tooling or docs.

## Failure modes

- **Tag on wrong SHA** — mitigated by recording candidate SHA in the release PR and using annotated tags.
- **Partial surface bump** (Rust vs Python) — mitigated by explicit per-surface version lines in release notes.
- **Skipped security path** for embargoed fixes — mitigated by [security-release-process.md](security-release-process.md).
