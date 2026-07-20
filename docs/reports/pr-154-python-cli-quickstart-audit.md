# Python CLI quickstart documentation audit

## Summary

This pull request adds and expands Python CLI quickstart documentation across the root README, CLI reference, local quickstart, and Python package README.

The changes are documentation-only and do not modify executable application logic.

## Files changed

| File | Change |
|------|--------|
| `README.md` | Adds a link to the Python CLI quickstart documentation. |
| `docs/cli-reference.md` | Adds a concise Python CLI quickstart section. |
| `docs/quickstart-5min.md` | Corrects the expected exit-code description for the BLOCKED result. |
| `python/README.md` | Adds installation, first-command, expected-output, and troubleshooting guidance. |

## Evaluation gate

Status: pass.

Evidence:
- The root README links to the Python CLI quickstart.
- The CLI reference includes installation and first-command guidance.
- The Python package README includes expected output and troubleshooting information.
- The local quickstart contains the corrected BLOCKED exit-code expectation.
- No Rust or Python runtime implementation is changed.
- No dependency or lockfile changes are included.
- The pull request targets the required `staging` branch.

## Security assessment

Risk level: low.

The changes are documentation-only. They do not alter authentication, authorization, cryptographic behavior, dependency resolution, network access, secret handling, or runtime execution.

The documented commands should still be reviewed to ensure they do not encourage unsafe installation or execution practices.

## Compliance assessment

The change does not weaken or bypass governance controls, compliance checks, evidence generation, audit mechanisms, or repository enforcement rules.

The required audit report is included for traceability of the documentation change.

## Validation

The following validation applies:

- Markdown and repository formatting checks
- Documentation link validation
- Python package installation in a disposable virtual environment
- Python CLI version command
- Python CLI quickstart command and expected output
- Required compliance workflows
- Required pull-request checks

## Human approval gate

Status: pending maintainer review.

Reviewer: Monika Dvořáčková
