# Core governance convergence audit (PR A)

**Date:** 2026-06-10  
**Scope:** GovAI Core (`govai-core`) — canonical governance runtime copy  
**Source reference:** GovAI Engine (`aigov-compliance-engine`) cherry-picks only; no Engine dependency added.

## Summary

GovAI Core now owns the shared `AIGOV_*` / `GOVAI_*` environment resolution layer and the latest governance-runtime fixes that previously existed only in Engine. Core semantics remain canonical: `GovAIClient` naming, `runtime_key_lookup_enabled()`, lineage fields on `EvidenceEvent`, and `--from-evidence` offline digest mode in `write_digest_manifest.py`.

## Files changed

| Path | Action |
|------|--------|
| `rust/src/aigov_env.rs` | **Added** — copied from Engine |
| `rust/src/lib.rs` | **Updated** — `pub mod aigov_env` |
| `rust/src/audit_store.rs` | **Updated** — Engine fixes |
| `rust/src/audit_api_key.rs` | **Updated** — `aigov_env` dual-key lookup |
| `rust/src/policy_engine.rs` | **Updated** — `FromStr` + unit test |
| `rust/src/policy_store.rs` | **Updated** — `.parse()` for unknown event behavior |
| `rust/src/projection.rs` | **Updated** — `and_then` for risk review decision |
| `python/aigov_py/cli_config.py` | **Updated** — AIGOV config/URL/API key aliases |
| `python/aigov_py/write_digest_manifest.py` | **Updated** — AIGOV audit URL/API key defaults |
| `python/tests/test_cli_config_env_aliases.py` | **Added** — parity tests for env aliases |

## Copied from Engine and why it belongs in Core

### `rust/src/aigov_env.rs` (new)

Copied wholesale from Engine. Centralizes `AIGOV_*` → `GOVAI_*` fallback for database URLs, feature flags, and operator env vars. Belongs in Core because every governance runtime consumer (Rust crate, Python CLI, future Engine dependency) needs one canonical resolver — not a second copy in Engine.

### `rust/src/audit_store.rs`

| Fix | From Engine | Rationale |
|-----|-------------|-----------|
| `const { Cell::new(0) }` in test `thread_local!` | Yes | Rust 2024 const-init for thread locals |
| `aigov_env::required("AIGOV_SKIP_FSYNC", "GOVAI_SKIP_FSYNC")` | Yes | Dual-env fsync skip for CI/dev |
| `len.saturating_sub(win)` | Yes | Safer window math on ledger repair |

Core lineage test helpers and schema fields were **not** removed (Engine had dropped lineage in tests; Core keeps canonical lineage).

### `rust/src/policy_engine.rs` + `rust/src/policy_store.rs`

| Fix | From Engine | Rationale |
|-----|-------------|-----------|
| `impl std::str::FromStr for UnknownEventTypeBehavior` | Yes | Standard Rust parsing; policy loader uses `.parse()` |
| Unit test for `FromStr` | Added in Core | Parity for behavior change |

### `rust/src/projection.rs`

| Fix | From Engine | Rationale |
|-----|-------------|-----------|
| `risk_review_decision` via `.and_then()` | Yes | Clearer optional flattening; same semantics |

### `rust/src/audit_api_key.rs`

| Fix | From Engine | Rationale |
|-----|-------------|-----------|
| `aigov_env::required` for API key env vars | Yes | `AIGOV_API_KEYS`, `AIGOV_API_KEYS_JSON`, `AIGOV_API_KEY_DEFAULT_LIMIT`, `AIGOV_HOSTED_SELF_SERVICE` |

**Core-only:** function name remains `runtime_key_lookup_enabled()` (Engine renamed to `hosted_self_service_enabled()`).

### `python/aigov_py/cli_config.py`

| Fix | From Engine | Rationale |
|-----|-------------|-----------|
| `AIGOV_CONFIG` before `GOVAI_CONFIG` | Yes | Canonical config path resolution |
| Expanded audit base URL env list (`AIGOV_AUDIT_BASE_URL`, `AIGOV_BASE_URL`, …) | Yes | Operator alias parity |
| `AIGOV_API_KEY` before `GOVAI_API_KEY` | Yes | CLI/SDK env parity |

### `python/aigov_py/write_digest_manifest.py`

| Fix | From Engine | Rationale |
|-----|-------------|-----------|
| `AIGOV_AUDIT_BASE_URL` / `AIGOV_API_KEY` in HTTP defaults | Partial | Env alias parity only |

**Core-only:** `--from-evidence` offline mode retained (Engine removed it; Core CI depends on it).

### Not copied (intentional)

| Path | Engine diff | Reason skipped |
|------|-------------|----------------|
| `python/aigov_py/evidence_artifact_gate.py` | `GovAI*` → `AIGov*` renames | Core canonical SDK names are `GovAIClient`, `GovAIHTTPError`, etc. |
| `python/aigov_py/env_resolution.py` | Docstring wording | No behavioral change |
| `python/aigov_py/standards/registry.py` | Docstring wording | No behavioral change |

## Test results

```
cd rust && cargo test
  lib unit tests:     109 passed
  integration test:     1 passed  (runtime_core_integration)
  total Rust:         110 passed

cd python && python -m pytest
  404 passed, 2 skipped
```

New/updated parity coverage:

- `rust/src/aigov_env.rs` — `optional_prefers_aigov_over_govai`, `flag_truthy_accepts_on_and_yes`
- `rust/src/policy_engine.rs` — `unknown_event_type_behavior_from_str`
- `python/tests/test_cli_config_env_aliases.py` — config path, audit URL aliases, API key preference

## No dependency on Engine

Verified:

- No `Cargo.toml` path dependency on Engine
- No Python import of Engine packages
- All `aigov_env` and governance fixes are **in-tree copies** in `govai-core`
- Grep for runtime imports of `aigov-compliance-engine` in `rust/` and `python/aigov_py/` returns no matches (only historical paths in docs, migration scripts, and captured evidence JSON)

## Next step (out of scope for PR A)

Engine should adopt `govai-core` as a dependency (PR C) and delete duplicated governance paths (PR D) once packaging lands (PR B).

## Evaluation gate

Status: pass.

Evidence:
- cargo test: 110 passed
- python -m pytest: 404 passed, 2 skipped
- Core has no Rust, Python, or path dependency on Engine
- No phase-numbered labels, targets, or comments were introduced

## Human approval gate

Status: pending human review.

Reviewer: Monika Dvořáčková
Scope: Core governance runtime convergence with Engine fixes
