# Hosted runtime residue cleanup

**Date:** 2026-05-22  
**Scope:** GovAI Core repository — remove CI/Makefile assumptions that Core is a hosted HTTP audit SaaS runtime.

## Architectural intent

GovAI Core is **portable governance runtime infrastructure** (evidence semantics, digest continuity, offline validation). **Hosted control-plane lifecycle** (background audit HTTP service, `GET /ready` polling, ledger POST smoke in CI) belongs to the **GovAI Platform** repository or operator self-host stacks — not this repo’s default CI path.

This pass **does not** add stub servers, fake readiness, or localhost emulators.

---

## Changed files

| Path | Change |
|------|--------|
| `.github/workflows/govai-ci.yml` | Replaced hosted-audit job with `govai-core-portable` (Rust digest build, `make gate`, offline portable bundle + `verify-evidence-pack --portable-only`). |
| `.github/workflows/compliance.yml` | Removed Postgres service from `make_verify`; removed hosted `govai-compliance-gate` jobs; `evidence_pack` uses offline `scripts/ci_portable_artifact_bundle.py` + portable verify. |
| `.github/workflows/govai-smoke.yml` | Documented as **manual** operator smoke against external `GOVAI_AUDIT_BASE_URL` (not Core CI). |
| `Makefile` | Neutralized `audit_bg` / `audit_stop` / `audit_restart` / `audit_logs` / `check_audit`; `require_audit_url` for operator URLs; `audit` runs offline digest binary only. |
| `scripts/ci_portable_artifact_bundle.py` | **New** — deterministic offline CI artefact bundle (no HTTP audit server). |
| `python/aigov_py/write_digest_manifest.py` | `--from-evidence` for offline digest manifest generation. |
| `python/aigov_py/cli.py` | `verify-evidence-pack --portable-only`; hosted hints updated; fixed duplicate summary on portable success. |
| `python/tests/test_compliance_workflow_contract.py` | Contract tests updated for portable `evidence_pack` (no `govai-compliance-gate`, no `/ready`). |
| `python/tests/test_workflow_compliance_invariants.py` | `govai-ci` / `compliance` invariant tests updated for portable CI. |
| `docs/reports/hosted-runtime-residue-cleanup.md` | This report. |

---

## Removed hosted assumptions

### GitHub Actions

- `make audit_bg` / background `aigov_audit` or `portable_evidence_digest_once` as HTTP server
- `localhost:8088` / `GOVAI_AUDIT_BASE_URL: http://127.0.0.1:8088` in compliance CI
- `GET /ready`, `/status`, `/metrics` polling loops
- Postgres + sqlx migration startup solely to support local audit API in compliance PR gate
- Hosted evidence POST smoke (`POST /evidence`, `post_local_ev`, `make run` pipeline against local audit)
- Jobs `govai-compliance-gate` and `govai-compliance-gate-fork-pr-block` (hosted `submit-evidence-pack` + hosted-only verify)
- Miswired `evidence_pack` job that depended on HTTP readiness while job id was `typescript-sdk`

### Makefile

- Default implicit `http://127.0.0.1:8088` as Core-owned runtime
- `check_audit` readiness polling target
- SaaS lifecycle helpers (`audit_bg`, `audit_stop`, …) — now exit 2 with Platform pointer
- Targets that assumed Core starts audit without `GOVAI_AUDIT_BASE_URL` (`demo`, `flow_full`, `run`, etc. use `require_audit_url`)

### CLI / scripts

- `verify-evidence-pack` requiring `/bundle-hash` and compliance-summary HTTP for **CI portable gate** (bypassed via `--portable-only`)
- Error hints referencing `make audit_bg` for Core-local server startup

---

## CI normalization

| Workflow | Role after cleanup |
|----------|-------------------|
| `govai-ci.yml` | Portable: build digest helper, governance standards, doc gate, pytest portable tests, offline artefact bundle + portable verify. |
| `compliance.yml` | Report hygiene + `make gate` (no DB service) + portable `evidence_pack` when core/report changes require artefact gate. |
| `govai-smoke.yml` | **Manual only** — external hosted URL; not part of Core portable CI. |
| `nightly-full-validation.yml` / `release-validation.yml` | Unchanged in this pass; may still use Postgres for broader Rust/DB tests — **not** localhost audit orchestration. |

**Branch protection note:** If GitHub required checks still list `govai-compliance-gate`, update repository rules to require `evidence_pack` (and other `compliance.yml` jobs) instead. That rename is an operator/GitHub settings step outside this file change.

---

## Makefile / runtime cleanup

- **`audit`**: `cargo run --bin portable_evidence_digest_once` (offline digest CLI, not HTTP server).
- **`audit_bg` et al.**: Disabled in Core; message points to GovAI Platform.
- **`check_audit`**: Disabled; use portable CI script or operator `GOVAI_AUDIT_BASE_URL`.
- **`local-demo` / `fail-closed-demo`**: Retained as **optional operator demos** when an external runtime exists; Core does not start it.
- **Portable CI entrypoint:** `python3 scripts/ci_portable_artifact_bundle.py` + `govai verify-evidence-pack --portable-only` (or `python3 -m aigov_py.cli`).

---

## Remaining hosted assumptions (intentional or doc debt)

These are **not** Core CI orchestration but still reference hosted HTTP semantics for operators, examples, or separate workflows:

| Area | Notes |
|------|--------|
| `examples/local-demo/`, `examples/docker-compose-local-demo/`, `docker-compose.yml` | Operator-local demos; default `127.0.0.1:8088` when **user** runs compose/Platform stack. |
| `examples/blocked_deployment.sh`, `scripts/run_fail_closed_demo.py` | Require running audit API + keys (Platform/self-host). |
| `.github/workflows/govai-smoke.yml` | Manual workflow; requires `GOVAI_AUDIT_BASE_URL`. |
| `.github/actions/govai-check/` | Composite action for **consumer** repos with hosted audit URL. |
| `python/aigov_py/fetch_bundle_from_govai.py` | Default base URL fallback may still mention localhost for dev ergonomics. |
| Documentation (`README.md`, `docs/github-action.md`, `docs/quickstart-5min.md`, `DEMO_FLOW.md`, …) | Still describe hosted gate names (`govai-compliance-gate`) and `make audit_bg` in places — **documentation drift**; update in a follow-up docs pass. |
| `nightly-full-validation.yml` / `release-validation.yml` | Postgres for extended validation, not PR portable gate. |

**Validation grep (Core CI workflows):** no `audit_bg`, no `8088/ready` polling, no `govai-compliance-gate` job definitions in `govai-ci.yml` or `compliance.yml`.

---

## Final architectural consistency assessment

| Criterion | Status |
|-----------|--------|
| Core CI does not start localhost hosted audit runtime | **Met** (`govai-ci`, `compliance` `evidence_pack`) |
| No readiness polling loops in Core CI | **Met** |
| No hosted SaaS lifecycle management in Makefile defaults | **Met** (stubs exit 2; operator URL required for HTTP flows) |
| Portable evidence/digest/replay validation preserved | **Met** (offline bundle + `--portable-only`) |
| No fake/stub HTTP servers introduced | **Met** |
| Deterministic governance / doc gates preserved | **Met** (`make gate`, `governance-standards-check`) |

**Conclusion:** GovAI Core CI and Makefile defaults now align with **portable governance runtime infrastructure**. Hosted ledger submission and HTTP compliance gates remain available via **explicit operator configuration** (`GOVAI_AUDIT_BASE_URL`, manual `govai-smoke`, Platform repo), not as implicit Core CI behavior.

---

## Verification performed

- `python3 -m pytest tests/test_compliance_workflow_contract.py tests/test_workflow_compliance_invariants.py` — 12 passed
- Local: `scripts/ci_portable_artifact_bundle.py` + `python3 -m aigov_py.cli verify-evidence-pack --portable-only` — exit 0, single `PORTABLE_OK` summary

## Evaluation gate

Passed. The branch was evaluated against the repository governance and compliance gate expectations.

## Human approval gate

Pending maintainer review before merge.
