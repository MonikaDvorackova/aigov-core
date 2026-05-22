# GovAI Compatibility Policy

## Purpose

This document defines GovAI's compatibility and stability guarantees.

The goal of this policy is to provide clear expectations for users, contributors, and enterprise adopters regarding API stability, semantic versioning, deprecation, and backward compatibility.

## Semantic Versioning

GovAI follows Semantic Versioning.

Version numbers are structured as:

MAJOR.MINOR.PATCH

- MAJOR versions introduce breaking changes.
- MINOR versions add backward-compatible functionality.
- PATCH versions provide backward-compatible bug fixes.

## Public Interfaces Covered by This Policy

This policy applies to the following interfaces:

- Python package `aigov_py`
- Command line interface
- Rust HTTP API
- GitHub Action inputs and outputs
- Evidence bundle schemas
- Audit export formats
- Docker Compose examples
- Documentation examples

## Compatibility Guarantees

### Patch Releases

Patch releases will not introduce breaking changes.

### Minor Releases

Minor releases will preserve backward compatibility except where explicitly documented.

### Major Releases

Major releases may introduce breaking changes and migration steps.

## Deprecation Policy

Features scheduled for removal will be:

1. Marked as deprecated in documentation.
2. Announced in the changelog.
3. Maintained for at least one minor release where practical.
4. Accompanied by migration guidance.

## API Stability Expectations

### Python CLI

Existing commands and options should remain stable across patch and minor releases.

### HTTP API

Public endpoints should remain stable unless explicitly deprecated.

### GitHub Action

Published action inputs and outputs are treated as public contracts.

### Evidence Schemas

Changes should preserve compatibility whenever feasible.

## Experimental Features

Experimental features may change without compatibility guarantees.

Experimental status will be clearly documented.

## Documentation Accuracy

Examples and tutorials should match the current stable release.

## Migration Guidance

Breaking changes should include:

- Changelog entries
- Upgrade notes
- Migration examples

## Enterprise Considerations

Compatibility is a core requirement for regulated and enterprise deployments. Changes that affect auditability, evidence integrity, or enforcement semantics must be documented carefully.

## Summary

GovAI aims to provide predictable, stable interfaces while preserving the ability to evolve the platform. Compatibility guarantees are governed by Semantic Versioning and explicit deprecation procedures.
