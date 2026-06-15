# Ready integration CI determinism audit

## Summary

This change fixes a CI-only failure in the runtime integration test for `GET /ready`.

`release-validation.yml` sets `DATABASE_URL` for the job. When a database URL is present, readiness includes database checks, including migration completeness. The integration test built runtime state without enabling automatic migrations, so `/ready` returned `503` in CI while passing locally when no database was configured.

## Files changed

| File | Change |
|------|--------|
| `rust/tests/runtime_core_integration.rs` | Enables `GOVAI_AUTO_MIGRATE=true` for the integration harness when `DATABASE_URL` is configured, initializes the test ledger parent directory, and prints `/ready` JSON diagnostics on failure. |

## Runtime behavior

Runtime readiness semantics are unchanged.

`GET /ready` remains non-mutating and still fails closed when configured readiness checks fail.

## Validation

- `cargo test --locked`
- `cargo test --locked --test runtime_core_integration -- --nocapture`
- `python -m pytest -q`
- `python scripts/gate_reports.py`
- `make cursor-plugin-smoke`
- `make release-readiness-check`

## Evaluation gate

Status: pass.

Evidence:
- `/ready` integration test passes with database readiness enabled.
- The test still asserts non-mutating readiness behavior.
- Runtime readiness semantics were not weakened.

## Human approval gate

Status: pending maintainer review.

Reviewer: Monika Dvořáčková
