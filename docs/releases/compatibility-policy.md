# Compatibility policy

## Purpose

Clarify what **“compatible”** means for GovAI HTTP APIs, CLI contracts, documented environment variables, and portable standards interchange so consumers can plan upgrades safely.

## Policy

- **PATCH** releases preserve wire-compatible JSON shapes for **documented** stable endpoints and **non-experimental** CLI flags unless fixing a documented bug where the previous behaviour was clearly unintended.
- **MINOR** releases may add optional fields, new endpoints, new CLI subcommands, and new interchange artefact types **without** breaking existing consumers that ignore unknown fields.
- **MAJOR** releases may remove or rename fields, change verdict semantics where externally visible, or change default enforcement modes **only** when called out in release notes and **CHANGELOG**, with migration guidance.
- **Experimental** surfaces (explicitly marked in docs or code) may change in **MINOR** until promoted to stable.

## Maintainer actions

- Classify each release per [versioning-policy.md](versioning-policy.md) before tagging.
- Document **additive** schema changes in release notes; run interchange validators when `examples/standards/` or schemas change.

## Contributor expectations

- Mark experimental features in docs and PR titles when possible.
- Add tests and docs for new stable fields or endpoints.

## Failure modes

- **Implicit contracts** (undeclared JSON fields relied on by integrators) — mitigated by documenting stable response shapes in `docs/` and OpenAPI where published.
- **Digest or canonicalisation drift** in standards — mitigated by evaluation harness and explicit **MAJOR**/**MINOR** classification.
