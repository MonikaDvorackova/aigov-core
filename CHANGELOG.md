# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to the [versioning policy](docs/releases/versioning-policy.md).

## [Unreleased]

### Added

- Release engineering subsystem: **`docs/releases/release-manifest.json`**, **`scripts/validate_release_manifest.py`**, **`scripts/validate_changelog.py`**, **`scripts/generate_release_notes.py`**, **`scripts/release_readiness_report.py`**, **`examples/releases/`** driver scripts, pytest coverage, Makefile targets (**`release-manifest`**, **`validate-changelog`**, **`generate-release-notes`**, **`release-readiness-report`**, expanded **`release-readiness-check`**), and CI artefacts (**`release-manifest-validation.json`**, **`changelog-validation.json`**, **`release-readiness-report.json`**, **`release-notes-template.md`**).

### Changed

- **`scripts/release_operations_check.py`** now embeds manifest and changelog validation and requires the expanded Makefile release target set.
- **`README.md`**, **`CONTRIBUTING.md`**, **`docs/index.md`**, **`docs/project/local_development.md`**, and **`docs/project/contributor_workflow.md`** document the new commands and examples.
