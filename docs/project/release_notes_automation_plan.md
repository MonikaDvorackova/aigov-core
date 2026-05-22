# GovAI Release Notes Automation Plan

## Purpose

This document defines the plan for release notes automation in GovAI.

Release notes automation should make releases consistent, auditable, and easier to prepare. It should reduce manual work while preserving human review for security, governance, and compatibility-sensitive changes.

## Goals

Release notes automation should help maintainers:

1. Summarize merged pull requests
2. Group changes by category
3. Link releases to changelog entries
4. Identify breaking changes
5. Identify compatibility-sensitive changes
6. Identify security-sensitive changes
7. Prepare consistent GitHub Releases

## Release Note Categories

Release notes should group changes into the following categories:

1. Added
2. Changed
3. Deprecated
4. Removed
5. Fixed
6. Security
7. Documentation
8. Internal

## Pull Request Requirements

Pull requests should ideally include labels that support release note generation.

Recommended labels:

1. type:feature
2. type:fix
3. type:docs
4. type:security
5. type:breaking
6. type:internal
7. area:python
8. area:rust
9. area:ci
10. area:docs
11. area:governance

## Automation Strategy

The initial release notes automation should use GitHub-native tooling where possible.

Recommended approach:

1. Use GitHub labels to classify pull requests
2. Generate draft release notes from merged pull requests
3. Review the generated release notes manually
4. Copy material into CHANGELOG.md where appropriate
5. Publish GitHub Release after maintainer approval

## GitHub Release Drafting

The project may use GitHub's automatic release notes generation as the first implementation step.

This keeps the process simple and avoids introducing unnecessary release tooling too early.

## Human Review Requirements

Generated release notes must be reviewed by a maintainer before publication.

Human review is required for:

1. Breaking changes
2. Security changes
3. Evidence schema changes
4. API changes
5. GitHub Action input or output changes
6. Compliance verdict semantics
7. Tenant isolation changes
8. Billing behavior changes

## Compatibility Review

Before publishing a release, maintainers should check:

1. Whether public interfaces changed
2. Whether migration guidance is needed
3. Whether CHANGELOG.md needs an entry
4. Whether documentation examples remain accurate
5. Whether compatibility policy expectations are satisfied

## Release Checklist Integration

Release notes automation should integrate with the existing release checklist.

A release should not be published until:

1. Tests pass
2. Compliance gate passes
3. Changelog is updated
4. Release notes are reviewed
5. Compatibility impact is assessed
6. Security impact is assessed

## Future Automation

Future iterations may include:

1. Label-based release note generation workflow
2. Pull request title validation
3. Conventional commit support
4. Automated changelog proposal
5. Automated compatibility impact checklist
6. Release drafter configuration

## Acceptance Criteria

This work is complete when:

1. Release note categories are documented
2. Pull request label expectations are documented
3. Human review requirements are documented
4. Compatibility review requirements are documented
5. Future automation path is documented
6. The process aligns with CHANGELOG.md and the release checklist

## Summary

Release notes automation should make GovAI releases easier to prepare without weakening governance discipline. The process should stay human-reviewed for security, compatibility, and auditability-sensitive changes.
