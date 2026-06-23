# Quinn-proto RUSTSEC-2026-0185 remediation audit

## Summary

This change resolves `RUSTSEC-2026-0185` by updating `quinn-proto` from `0.11.14` to `0.11.15` in repository lockfiles.

## Root cause

`cargo audit` reported `quinn-proto` 0.11.14 as vulnerable to remote memory exhaustion from unbounded out-of-order stream reassembly. The advisory requires `>=0.11.15`.

## Dependency chain

`quinn-proto` is not a direct dependency. It is pulled in transitively through:

`reqwest` 0.12.28 → `quinn` 0.11.9 → `quinn-proto`

`reqwest` is declared in `rust/Cargo.toml` for HTTP client functionality used by the core runtime.

## Change

| File | Change |
|------|--------|
| `rust/Cargo.lock` | `cargo update -p quinn-proto` (`0.11.14` → `0.11.15`) |
| `tests/downstream-consumption/rust-consumer/Cargo.lock` | `cargo update -p quinn-proto` (`0.11.14` → `0.11.15`) |
| `rust/adapters/immutable_s3/Cargo.lock` | Manual lockfile bump for `quinn-proto` only (avoids broad adapter lock refresh) |

No `Cargo.toml` manifest changes were required.

## Validation

- `cargo audit` in `rust/` — pass
- `cargo test --all --locked -- --test-threads=1` in `rust/` — pass (151 tests)

## Risk assessment

Low.

This is a targeted patch-level security update to a transitive QUIC protocol dependency. No application code or public API behavior changed.

## Evaluation gate

Supply-chain audit CI (`supply-chain-audit.yml`) should pass `cargo audit` on the next run.

## Human approval gate

Reviewed before merge. Change scope is limited to lockfile resolution for `quinn-proto`.
