# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to the [versioning policy](docs/releases/versioning-policy.md).

## [Unreleased]

### Changed

- Repository slug and documentation branding: **`govai-core` → `aigov-core`** (GitHub rename prepared in-tree). Runtime package names unchanged (`aigov_audit`, `aigov-py`, `govai` CLI compat). Helm chart, Kubernetes manifests, Docker tags, and CI job `aigov-core-portable` use the new slug.

### Added

- *(none yet)*

## [0.2.1] - 2026-06-10

### Added

- Release packaging metadata for Rust (`rust/Cargo.toml`) and Python (`python/pyproject.toml`).
- Release validation scripts: `scripts/validate_changelog.py`, `scripts/generate_release_notes.py`, and `scripts/release_readiness_report.py` with Makefile targets and CI artifact build steps.
- Production-readiness fixes: non-mutating `GET /ready`, mounted `GET /metrics`, standards registry entries, and supply-chain CI (Dependabot, `supply-chain-audit` workflow).

### Changed

- PostgreSQL-only SQLx dependency graph (removed `sqlx-mysql` / `rsa` transitives); runtime migrations use `sqlx_core::migrate::Migrator`.
- Release documentation and examples aligned with scripts and Makefile targets shipped in AIGov Core (removed references to platform-only release validators).

### Fixed

- Runtime observability contract tests for `/metrics` and read-only readiness probes.
