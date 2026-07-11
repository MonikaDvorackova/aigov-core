# Enforce PR Branch Policy

## Summary

This change updates the GitHub Actions workflow that enforces the repository branch policy.

## Change

The workflow enforces the following policy:

- Feature, documentation, and contributor branches must target staging.
- Only staging may open a pull request into main.

## Rationale

The repository follows the branch workflow:

feature branch -> staging -> main

This prevents accidental direct pull requests into main.

## Evaluation gate

Validation scope:

- feature/docs -> staging: expected pass
- feature/docs -> main: expected fail
- staging -> main: expected pass

No runtime, API, Rust crate, Python package, or governance primitive behavior is changed.

## Human approval gate

This workflow change requires maintainer review before merge because it affects repository merge policy.

Maintainer review should confirm that normal contributor work targets staging and that only staging can promote into main.

## Runtime impact

This change only affects GitHub Actions pull request branch policy enforcement.
