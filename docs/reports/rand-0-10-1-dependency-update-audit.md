# Rust dependency modernization audit

## Summary

This change modernizes selected Rust dependencies through the staging workflow after closing Dependabot pull requests that incorrectly targeted `main`.

The update includes dependency upgrades that were validated together because they affect shared runtime, cryptographic, and rate-limiting surfaces.

## Files changed

| File | Change |
|------|--------|
| `rust/Cargo.toml` | Updates selected Rust dependency versions. |
| `rust/Cargo.lock` | Refreshes resolved dependency graph. |
| `rust/src/govai_api.rs` | Updates route capture syntax for Axum 0.8. |
| `rust/src/http_observability.rs` | Aligns route normalization strings with Axum 0.8 capture syntax. |

## Dependency notes

Axum 0.8 requires route captures to use `{capture}` instead of `:capture`.

The following route patterns were updated:

- `/bundle/{run_id}`
- `/bundle-hash/{run_id}`
- `/compliance-summary/{run_id}`
- `/api/export/{run_id}`
- `/verify/{run_id}`

## Validation

- `cargo test`
- `cargo test --locked`
- `python -m pytest -q`
- `python scripts/gate_reports.py`
- `make cursor-plugin-smoke`
- `make release-readiness-check`

## Remaining limitations

`sha2` 0.11 is not included because it is blocked by `sqlx-core 0.8.6`, which requires `sha2 ^0.10`.

## Evaluation gate

Status: pass.

Evidence:
- Rust test suite passes after dependency updates.
- Runtime integration test passes with Axum 0.8 route syntax.
- Dependency updates are routed through `staging`.

## Human approval gate

Status: pending maintainer review.

Reviewer: Monika Dvořáčková
