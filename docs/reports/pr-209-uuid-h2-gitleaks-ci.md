# PR #209 — UUID, h2, and Gitleaks CI update

## Summary

This pull request updates the Rust `uuid` dependency from 1.24.0 to 1.25.0, upgrades the vulnerable transitive `h2` dependency from 0.4.15 to 0.4.16, and replaces the license-dependent Gitleaks GitHub Action with the open-source Gitleaks CLI.

## Scope

- update `uuid` from 1.24.0 to 1.25.0
- update `h2` from 0.4.15 to 0.4.16 to address RUSTSEC-2026-0258
- install the Gitleaks CLI directly without requiring `GITLEAKS_LICENSE`
- scope pull-request secret scanning to commits introduced by the pull request

## Risk assessment

The dependency updates may introduce compatibility or transitive dependency changes. The Gitleaks workflow change may affect secret-scan coverage if the pull-request commit range is calculated incorrectly. Existing repository history is intentionally excluded from the pull-request scan because it contains previously committed example authorization headers that produce known findings.

## Mitigations

- Rust workspace tests and `cargo audit` remain required
- Gitleaks remains pinned to version 8.30.1
- pull-request scans cover the complete base-to-head commit range
- non-pull-request executions scan the current commit
- all existing required CI and compliance gates remain enabled

## Evaluation gate

The change is acceptable only if the Rust test suite, dependency audit, Gitleaks secret scan, repository gate, and all required CI checks pass against `staging`.

## Human approval gate

Pending. This report does not claim human approval. Merge requires approval by an authorized repository maintainer.

## Rollback plan

Revert this pull request to restore the previous Rust lockfile and Gitleaks workflow configuration. If only the CI change causes failure, restore `gitleaks/gitleaks-action@v2` together with a valid organization license or replace the CLI invocation with another approved secret-scanning implementation.

## Result

The pull request is suitable for merge only after all required automated checks pass and an authorized maintainer approves it.
