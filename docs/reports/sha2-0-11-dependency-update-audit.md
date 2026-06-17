# sha2 0.11 dependency update audit

## Summary

This change updates the Rust `sha2` dependency to `0.11.0` through the staging workflow.

## Files changed

| File | Change |
|------|--------|
| `rust/Cargo.toml` | Updates `sha2` dependency version. |
| `rust/Cargo.lock` | Refreshes resolved Rust dependency graph. |

## Validation

- `cargo test --locked`

## Evaluation gate

Status: pass.

Evidence:
- Rust tests pass with `sha2` 0.11.0.
- Dependency update is routed through `staging`, not directly to `main`.

## Human approval gate

Status: pending maintainer review.

Reviewer: Monika Dvořáčková
