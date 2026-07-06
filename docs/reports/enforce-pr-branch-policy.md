# Enforce PR Branch Policy

## Summary

This change updates the GitHub Actions workflow that enforces the repository branch policy.

## Change

The workflow now enforces the following policy:

- Feature, documentation, and contributor branches must target staging.
- Only staging may open a pull request into main.

## Rationale

The repository follows the branch workflow:

feature branch → staging → main

This prevents accidental direct pull requests into main.

## Validation

- feature/docs → staging: pass
- feature/docs → main: fail
- staging → main: pass

## Runtime impact

No runtime, API, library, or governance functionality is modified. This change only affects the GitHub Actions workflow.
