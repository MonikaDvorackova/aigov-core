# Audit report: ed25519-dalek 3.0.0 update

## Summary

Updates the Rust dependency `ed25519-dalek` to version `3.0.0`.

## Scope

The change is limited to dependency metadata and generated lockfiles.

## Evaluation gate

- Reviewed the dependency update and transitive dependency changes.
- Verified that downstream Rust consumer lockfiles are updated.
- Confirmed that no application behavior, API contract, tenant isolation, ledger semantics, or evidence handling is intentionally changed.

## Human approval gate

This dependency update requires maintainer review before merge.

## Validation

- `cargo test --locked`
- downstream consumption checks
- repository CI checks
