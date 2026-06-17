# Cargo lockfile refresh audit

## Summary

This change refreshes `rust/Cargo.lock` after Rust dependency updates so locked CI jobs can run without attempting to modify the lockfile.

## Files changed

| File | Change |
|------|--------|
| `rust/Cargo.lock` | Refreshes resolved dependency graph after dependency modernization and release conflict resolution. |

## Validation

- `cargo metadata --locked --format-version 1`
- `cargo audit`
- `cargo test`

## Evaluation gate

Status: pass.

Evidence:
- `Cargo.lock` is parseable.
- Locked Cargo commands no longer need to update the lockfile.
- Dependency updates remain routed through staging.

## Human approval gate

Status: pending maintainer review.

Reviewer: Monika Dvořáčková
