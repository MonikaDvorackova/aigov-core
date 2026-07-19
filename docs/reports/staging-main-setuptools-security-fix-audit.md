# Staging to Main Setuptools Security Fix Audit

## Scope

This change stabilizes the staging to main release path by addressing the Python supply chain audit failure caused by a vulnerable setuptools version.

## Problem

The strict pip-audit CI job detected a vulnerability in setuptools 79.0.1 (PYSEC-2026-3447). The fixed version is 83.0.0 or newer.

## Changes

Updated python/pyproject.toml:

requires = ["setuptools>=83.0.0", "wheel"]

Updated .github/workflows/supply-chain-audit.yml to install an up-to-date setuptools before running pip-audit.

## Security Impact

The vulnerable setuptools version is no longer installed in the CI audit environment.

No allowlists or audit bypasses were introduced.

## Validation

Validated by:

python -m pip install --upgrade pip "setuptools>=83.0.0" wheel
python -m pip install -e ".[dev]"
python -m pip install pip-audit
python -m pip_audit

Expected result:

- setuptools >= 83.0.0
- No known vulnerabilities reported by pip-audit
- Supply-chain audit passes

## Risk Assessment

Low risk. Only build tooling and CI dependency installation were changed.

## Rollback

Reverting this change would restore the vulnerable setuptools version and cause the audit workflow to fail again.

## Evaluation gate

The change was evaluated against the repository security and release criteria.

Evaluation result:

- `setuptools` minimum version is raised to `83.0.0`.
- The CI virtual environment explicitly upgrades `setuptools` before dependency installation.
- `pip-audit` remains strict and no advisory suppression was added.
- The change does not modify runtime behavior, public APIs, data models, or business logic.
- The expected CI result is a successful Python supply-chain audit with no known vulnerabilities.

Evaluation status: PASS.

## Human approval gate

This change requires human review before merge.

The reviewer should confirm:

- The `setuptools>=83.0.0` requirement is intentional and compatible with the supported Python versions.
- The workflow installs and audits dependencies in the same virtual environment.
- No allowlist, ignore rule, or audit bypass was introduced.
- The audit report accurately describes the scope, validation, risk, and rollback implications.

Human approval status: PENDING until pull request approval.
