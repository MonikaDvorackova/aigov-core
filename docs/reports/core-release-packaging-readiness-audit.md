# AIGov Core release and packaging readiness audit

## Summary

This change set improves AIGov Core release metadata, documentation accuracy, validation scripts, and CI artifact builds without publishing to public registries. Platform-only release validators referenced after the open-core split were removed from manifests and docs; only scripts present in this repository are referenced.

## Files changed

| Path | Change |
|------|--------|
| `rust/Cargo.toml` | Added `license`, `description`, `repository`, `readme`, `keywords`, `categories` |
| `python/pyproject.toml` | Added `license`, `authors`, `classifiers`, `[project.urls]`, package `readme` |
| `python/README.md` | Package-local README for setuptools/PyPI long description |
| `CHANGELOG.md` | Added dated `[0.2.1]` section; cleared false Unreleased claims |
| `Makefile` | Added `validate-changelog`, `generate-release-notes`, `release-readiness-report`, `release-readiness-check` |
| `scripts/release_lib.py` | Shared stdlib helpers for release scripts |
| `scripts/validate_changelog.py` | Keep a Changelog + version alignment validator |
| `scripts/generate_release_notes.py` | Deterministic release notes from CHANGELOG |
| `scripts/release_readiness_report.py` | Aggregated packaging readiness JSON report |
| `python/tests/test_validate_changelog.py` | Tests for changelog validator |
| `python/tests/test_generate_release_notes.py` | Tests for release notes generator |
| `python/tests/test_release_readiness_report.py` | Tests for readiness report |
| `.github/workflows/release-validation.yml` | Release metadata checks; `release-artifacts` job (wheel/sdist, `cargo package`, Docker tar upload) |
| `docs/releases/release-manifest.json` | Removed stale platform-only script/check references |
| `docs/releases/release-checklist.md` | Aligned with Core Makefile and test commands |
| `docs/releases/release-runbook.md` | Removed `release_operations_check.py` reference |
| `docs/index.md` | Updated release command index |
| `docs/project/contributor_workflow.md` | Updated release Makefile/pytest references |
| `examples/releases/README.md` | Removed manifest validation driver |
| `examples/releases/sample-release-plan.json` | Updated pre-tag pytest list |
| `README.md` | Release section and Makefile table |
| `docs/project/local_development.md` | Updated release command examples |
| `examples/releases/run-release-manifest-validation.sh` | **Deleted** (referenced missing script) |

## Audit findings addressed

| Finding | Resolution |
|---------|------------|
| Missing Rust crate metadata | Populated `rust/Cargo.toml` publishing fields |
| Missing Python package metadata | Populated `python/pyproject.toml` with license, authors, classifiers, URLs, readme |
| CHANGELOG only `[Unreleased]` with false script claims | Added `[0.2.1] - 2026-06-10`; documented actual Core release tooling |
| Missing `scripts/validate_changelog.py` and related scripts | Implemented three stdlib validators/generators |
| Stale Makefile release targets in docs | Added real targets; updated checklist and README |
| References to `validate_release_manifest.py`, `release_operations_check.py`, `docs-links-strict` | Removed from manifest, examples, runbook, contributor docs |
| No CI release artifact build | Extended `release-validation.yml` with dry-run artifact job (no registry publish) |

## Validation commands

```bash
cd rust && cargo test --locked
cd python && python -m pytest -q
python3 scripts/gate_reports.py
make cursor-plugin-smoke
make release-readiness-check
python3 scripts/validate_changelog.py --json
python3 scripts/generate_release_notes.py --version 0.2.1 --json
python3 scripts/release_readiness_report.py --json
cd rust && cargo package --allow-dirty --no-verify
python -m pip install build && python -m build --outdir dist/python python
```

## Test results

| Check | Result |
|-------|--------|
| `cargo test --locked` | **PASS** (112 unit/integration tests) |
| `python -m pytest -q` | **PASS** (417 passed, 2 skipped) |
| `python3 scripts/gate_reports.py` | **PASS** |
| `make cursor-plugin-smoke` | **PASS** |
| `make release-readiness-check` | **PASS** |
| `scripts/validate_changelog.py --json` | **PASS** (`latest_released`: 0.2.1) |
| `scripts/release_readiness_report.py --json` | **PASS** (score 100) |
| `cargo package --no-verify` | **PASS** |
| `python -m build` (wheel + sdist) | **PASS** |

## Remaining release risks

- **Registry publish** is intentionally not automated; maintainers must configure credentials and explicit publish steps outside this workflow.
- **Docker image** CI artifact is a local `docker save` tar; operators still sign, scan, and promote images per their policy.
- **Version bump coordination** across Rust, Python, and CHANGELOG remains manual; `validate_changelog` enforces alignment but does not bump versions.
- **Platform-only doc paths** (for example `docs-links-strict` in older tutorials) may still mention targets not shipped in Core; release checklist no longer depends on them.
- **Tag push** triggers full `release-validation` plus `release-artifacts`; first tag build may need Docker layer cache tuning on cold runners.

## Engine independence

AIGov Core remains **Engine-independent**: no imports, workflows, or release gates reference `aigov-compliance-engine`. Release scripts operate on Core manifests, CHANGELOG, and packaging files only. Hosted Platform, billing, and proprietary validators stay out of this repository.

## Evaluation gate

Release packaging changes are validated by existing Core CI (`govai-ci`, `release-validation`) plus the new Makefile aggregate `release-readiness-check`. Documentation gate headings remain required in `docs/reports/*.md`. No ledger, tenant, or enforcement semantics were modified.

## Human approval gate

Maintainers must still approve tag creation, GitHub Release publication, and any external registry upload per [release-checklist.md](../releases/release-checklist.md) and [GOVERNANCE.md](../../GOVERNANCE.md). CI artifact upload does not constitute a production release.
