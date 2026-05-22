# GovAI Maintainer Guide

This guide defines maintainer expectations for GovAI.

## Maintainer responsibilities

Maintainers are responsible for:
- reviewing issues and pull requests
- preserving fail-closed semantics
- protecting auditability guarantees
- keeping contributor workflows clear
- maintaining documentation quality
- managing release readiness

## Issue triage

Issues should be triaged using:
- type labels
- priority labels
- architecture labels
- contributor labels

Good issues should include:
- summary
- problem
- goal
- acceptance criteria
- contributor notes

## Pull request review

PR review should check:
- correctness
- tests
- documentation impact
- security impact
- governance impact
- evidence continuity impact
- backwards compatibility

## Governance-sensitive changes

Extra care is required for changes affecting:
- VALID / INVALID / BLOCKED semantics
- audit ledger writes
- evidence bundle exports
- policy evaluation
- tenant isolation
- approval gates
- runtime enforcement
- cryptographic verification

## Merge expectations

Before merge, maintainers should verify:
- linked issue exists where appropriate
- validation steps are documented
- tests pass or failures are explained
- documentation is updated
- reports are included if required
- no secrets are committed

## Release readiness

Release readiness should include:
- CI passing
- evidence verification passing
- migration checks
- documentation review
- changelog or release notes
- security-sensitive changes reviewed

## Community conduct

Maintainers should keep reviews:
- specific
- technical
- respectful
- actionable

The goal is to make GovAI contributor-friendly while preserving high governance and auditability standards.
