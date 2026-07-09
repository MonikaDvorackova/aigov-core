# Core production-readiness fixes audit

**Date:** 2026-06-10  
**Scope:** GovAI Core (`govai-core`) — highest-priority production-readiness fixes (single PR)  
**Engine independence:** No imports, submodules, or runtime coupling to GovAI Engine / Platform. All changes are self-contained in Core.

## Issues addressed

| ID | Finding | Resolution |
|----|---------|------------|
| PR-1 | `GET /ready` appended ready-probe events (mutating) | Read-only `ledger_tenant_readable` check; removed append probes from `govai_api.rs` and `runtime_diagnostics.rs` |
| PR-2 | `GET /metrics` handler existed but was not mounted | Route added in `build_router`; observability contract updated |
| PR-3 | Three Python standards validators implemented but unregistered | `delegation_graph`, `capability_policy`, `trace_verification_plan` added to registry + dispatch tests |
| PR-4 | No supply-chain CI baseline | Dependabot (Cargo + pip) and `supply-chain-audit.yml` (`cargo audit`, `pip-audit`, strict) |
| PR-5 | README documented Makefile targets that do not exist | Replaced stale OSS/Makefile section with accurate Core targets only |
| PR-6 | Contradictory readiness docs (append probe vs non-mutating contract) | Updated operator/observability docs and OpenAPI |

## Files changed

| Path | Change |
|------|--------|
| `rust/src/ledger_storage.rs` | Added `default_tenant_ledger_readable()` + unit tests |
| `rust/src/runtime_diagnostics.rs` | Removed ledger append probe; emit `ledger_tenant_readable` |
| `rust/src/govai_api.rs` | Non-mutating `get_ready`; mount `GET /metrics` |
| `rust/tests/runtime_core_integration.rs` | Integration checks: repeated `/ready` does not grow ledger; `/metrics` returns Prometheus text |
| `python/aigov_py/standards/registry.py` | Register 3 additional artefact types + validator dispatch |
| `python/tests/test_standards_registry_dispatch.py` | **Added** — registry dispatch tests |
| `python/tests/test_standards_conformance.py` | Conformance over all six `examples/standards/*.valid.json` files |
| `scripts/check_runtime_observability.py` | Require `/metrics` in router |
| `.github/dependabot.yml` | **Added** — weekly Cargo + pip updates |
| `.github/workflows/supply-chain-audit.yml` | **Added** — strict `cargo audit` and `pip-audit` jobs |
| `api/govai-http-v1.openapi.yaml` | `ledger_tenant_readable` check; non-mutating `/ready` description |
| `docs/runtime-observability.md` | Non-mutating `/ready`; `/metrics` already documented |
| `docs/operator-diagnostics.md` | Removed append-probe guidance |
| `docs/reports/runtime-observability-diagnostics.md` | Read-only `/ready` wording |
| `README.md` | Accurate Makefile targets; removed stale platform-only `make` references |

## Validation commands

```bash
cd rust && cargo test
cd python && python -m pytest
python scripts/gate_reports.py
make cursor-plugin-smoke
make runtime-observability-check
```

## Test results

| Command | Result |
|---------|--------|
| `cargo test` | **112 passed** (111 unit + 1 integration), 0 failed |
| `python -m pytest` | **411 passed**, 2 skipped, 0 failed |
| `python scripts/gate_reports.py` | **passed** |
| `make cursor-plugin-smoke` | **passed** (4 smoke cases) |
| `make runtime-observability-check` | **passed** |

## Engine independence confirmation

- No files under `aigov-compliance-engine` were modified.
- No new dependency on Engine crates, Python packages, or hosted Platform routes.
- Core HTTP surface remains ledger-authoritative (`POST /evidence`, bundle/export/verify, compliance summary) plus operator probes (`/health`, `/ready`, `/status`, `/metrics`).
- Standards registry changes register **Core-owned** validators only; no Engine registry merge.

## Evaluation gate

**Replayed governance state remains ledger-authoritative.** `/ready` no longer appends evidence; repeated readiness probes cannot alter run counts, bundle hashes, or audit exports. Compliance verdicts still derive only from ingested ledger events and policy projection.

## Human approval gate

**Approval evidence remains append-only operational evidence.** Readiness and metrics endpoints are observability-only; they do not delete, rewrite, or synthesize `human_approved` events. Operators continue to detect BLOCKED runs via compliance APIs and ops logs — not via fabricated client-side verdicts.

## Remaining risks

- `cargo audit` / `pip-audit` may fail on first CI run if known advisories exist; no allowlist was added yet — address findings or document justified exceptions in a follow-up.
- JSON Schema files under `schemas/` for the three newly registered artefact types are still placeholders (same situation as the original three registry entries); schema publication is a separate docs artefact task.
- `make local-demo` intentionally exits non-zero in Core-only clones (Platform script not shipped); README now states this explicitly.
