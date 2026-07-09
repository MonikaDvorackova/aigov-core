# GovAI Core runtime test hardening audit

## Summary

This change set adds direct unit tests for compliance projection, export replay validation, and audit export building, extends the HTTP integration suite with replay validation on exported documents, and fixes log-chain continuity validation for run-scoped exports on multi-run ledgers.

## Files changed

| Path | Change |
|------|--------|
| `rust/src/projection.rs` | Added unit tests: valid lifecycle, blocked missing evidence, invalid evaluation, promotion edge cases, risk review propagation |
| `rust/src/replay_validation.rs` | Added focused validation tests; relaxed run-scoped log-chain genesis check for mid-ledger runs |
| `rust/src/audit_export.rs` | Added export tests: full event chain, schema shape, deterministic hashes, lineage block + replay validation |
| `rust/tests/runtime_core_integration.rs` | Extended suite with `run_export_validations` on HTTP export and lineage block assertion |

## Audit findings addressed

| Finding | Resolution |
|---------|------------|
| Projection logic lacked direct unit coverage | Five deterministic tests on `derive_current_state_from_events` and verdict coupling |
| Replay validation had minimal test surface | Tests for tampered digest, chain break, lifecycle violation, duplicates, schema rejection, lineage delegation errors |
| Audit export tests only checked schema version | Full-chain export, required top-level keys, deterministic digest, lineage inclusion, replay pass |
| Integration suite did not replay-validate exports | Golden-path export validated with `run_export_validations` |
| Chain continuity false positives on multi-run ledgers | First run-scoped `log_chain` row no longer required to use ledger genesis `prev_hash` |

## Validation commands

```bash
cd rust && cargo test --locked
cd python && python -m pytest -q
python3 scripts/gate_reports.py
make cursor-plugin-smoke
```

## Test results

| Check | Result |
|-------|--------|
| `cargo test --locked` | **PASS** (126 unit + 1 integration test) |
| `python -m pytest -q` | **PASS** (417 passed, 2 skipped) |
| `python3 scripts/gate_reports.py` | **PASS** |
| `make cursor-plugin-smoke` | **PASS** |

New Rust tests added: **18** (5 projection, 9 replay validation, 4 audit export; integration extension reuses existing suite).

## Remaining risks

- **JSON Schema validation** is structural (required keys) only; full schema validation against `docs/schemas/aigov.audit_export.v1.schema.json` remains a Python/CI concern.
- **Concurrent ledger tests** in the same process can race on shared env vars; CI uses sequential integration suite to avoid collisions.
- **Lineage delegation cycles** across multiple runs are covered in `lineage_validation` tests; replay validation tests use single-run delegation errors.
- **Policy gate permutations** (feature flags) remain in `policy::gate_tests`; projection tests use default policy verdict path only.

## Engine independence

All changes are confined to GovAI Core Rust runtime modules and Core integration tests. No references to `aigov-compliance-engine`, hosted Platform routes, or proprietary Engine validators were introduced.

## Evaluation gate

Runtime correctness is enforced by expanded Rust unit and integration tests. Existing compliance gates (`gate_reports.py`, cursor plugin smoke) remain unchanged. Log-chain validation now matches tenant ledger semantics for run-scoped exports.

## Human approval gate

No production promotion, tag, or registry publish is implied by this test-only hardening. Maintainers merge after CI green and optional manual review of replay-validation semantics for external export consumers.
