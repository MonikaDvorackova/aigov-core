# Versioning policy

## Purpose

Define how GovAI publishes **coordinated version numbers** across documentation, packaged artefacts, and interchange surfaces so operators, integrators, and contributors can reason about **compatibility and upgrade risk** without guessing.

## Policy

- **Semantic intent:** releases follow [Semantic Versioning 2.0.0](https://semver.org/) at the **product line** level: **MAJOR** for incompatible API or contract changes consumers must react to; **MINOR** for backward-compatible additions; **PATCH** for backward-compatible fixes. Where multiple versioned surfaces exist (for example Rust crates vs Python packages), maintainers publish a **single release tag** and document per-surface versions in [release notes](release-notes-template.md).
- **Source of truth:** the **Git tag** `vX.Y.Z` on the promoted commit is authoritative for the OSS release line. Pre-release identifiers (`-rc.N`, `-beta.N`) are allowed for staged promotion when documented in the release checklist.
- **Documentation versions:** reader-facing docs under `docs/` track the **same release line** as the tag; breaking doc-only clarifications that do not change runtime behaviour still ship with the **next** semver-appropriate release.
- **Interchange and schemas:** registry-backed JSON artefacts and JSON Schema revisions are versioned per [compatibility-policy.md](compatibility-policy.md); digest algorithms and canonical serialisation are **not** changed in PATCH releases except when fixing demonstrably broken determinism (treated as **PATCH** with explicit release notes).

## Maintainer actions

- Before tagging, confirm **CHANGELOG.md** has a dated **`[X.Y.Z]`** section moved from **Unreleased** with accurate subsections.
- Align **Rust** and **Python** package versions with the policy in [release-runbook.md](release-runbook.md) when those surfaces ship in the same tag.
- Publish **GitHub Releases** (or equivalent) using [release-notes-template.md](release-notes-template.md) and attach the same notes to the tag annotation when your tooling supports it.

## Contributor expectations

- Propose **semver impact** in PR descriptions when behaviour visible to operators or integrators may change.
- Do not silently rename public CLI flags, HTTP paths, or documented environment variables without an RFC or maintainer agreement and a **MINOR** or **MAJOR** bump per this policy.

## Failure modes

- **Drift:** multiple version numbers on the same tag confuse SBOM and support — mitigated by the release runbook and checklist.
- **Ambiguous pre-releases:** consumers pin `latest` and get unstable behaviour — mitigated by explicit `-rc` / `-beta` naming and release notes.
- **Doc-only “releases”** without tags fragment expectations — mitigated by tagging only complete release candidates that pass [release-checklist.md](release-checklist.md).
