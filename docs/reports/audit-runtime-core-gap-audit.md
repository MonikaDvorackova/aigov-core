# Audit runtime core completion — gap audit

Date: 2026-05-25  
Branch: `feature/audit-runtime-core-completion`  
Scope: GovAI Core only (ledger-authoritative audit runtime)

## Implemented gaps

| Gap | Resolution |
|-----|------------|
| No runnable HTTP binary | `rust/src/main.rs`, `aigov_audit` bin in `Cargo.toml`, `lib::run()` |
| No HTTP router | `rust/src/govai_api.rs` — ingest, bundle, bundle-hash, compliance-summary, export, verify, health, ready, status |
| No ledger-authoritative verdict | `rust/src/compliance_summary.rs` — `VALID` / `INVALID` / `BLOCKED` from projection + policy gates only |
| No audit export builder | `rust/src/audit_export.rs` — `aigov.audit_export.v1` per `docs/schemas/aigov.audit_export.v1.schema.json` |
| Missing policy ledger view | `rust/src/ledger_view.rs` — `FileLedgerView` for ingest-time gates |
| Missing metering module reference | `rust/src/metering.rs` — optional `GOVAI_METERING=on` diagnostics (no billing) |
| No SQL migrations | `rust/migrations/0001_core_api_key_usage.sql`, `0002_core_issued_api_keys.sql`; `EXPECTED_SQLX_MIGRATION_COUNT = 2` |
| No integration tests | `rust/tests/runtime_core_integration.rs` — in-process Axum suite |
| CI did not build/test runtime | `.github/workflows/govai-ci.yml` — `cargo build --bin aigov_audit`, `cargo test --locked` |
| Dockerfile / Makefile drift | Dockerfile copies `migrations/`; `make build-audit` / `make run-audit` |

## Architectural decisions

1. **Ledger authority** — Compliance verdict and export `decision.verdict` are derived only from append-only ledger events and `projection::ComplianceCurrentState`. Postgres AI decision traces are not consulted.

2. **Verdict ordering** — `INVALID` when `evaluation_passed == false`; `BLOCKED` for missing requirements, approval/promotion prerequisites, or reject decisions; `VALID` only when requirements are satisfied and `promotion.state == "promoted"`.

3. **Route shapes** — OpenAPI query forms (`/bundle?run_id=`) remain primary; path aliases (`/bundle/:run_id`) added for ergonomics without breaking existing clients.

4. **Postgres optional** — Ledger-only dev/CI works without `DATABASE_URL`; `/ready` skips DB checks when no URL is configured.

5. **Core boundary** — No Stripe, billing, pricing, onboarding, dashboard ACL, or `/api/compliance-workflow*` routes in the default router. Enterprise handlers remain in the crate behind the platform boundary but are not mounted on `aigov_audit`.

6. **Integration testing** — Single sequential in-process test suite avoids `GOVAI_API_KEYS_JSON` OnceCell races and ledger probe file collisions under parallel `cargo test`.

## CI coverage

| Check | Command / artifact |
|-------|-------------------|
| Build audit runtime | `cargo build --locked --bin aigov_audit` |
| Unit + integration tests | `cargo test --locked` (includes `runtime_core_integration`) |
| Portable digest (unchanged) | `cargo build --bin portable_evidence_digest_once`, `govai verify-evidence-pack --portable-only` |
| Migration count parity | `db::migration_count_tests` |

## Remaining non-core exclusions (intentional)

- Stripe / SaaS billing / entitlement gating
- Hosted background service orchestration (`make audit_bg` — exits with pointer to Platform repo)
- Compliance workflow product tables and HTTP console
- AI decision trace ingest as authoritative verdict
- Web Analytics / log drains / commercial pricing endpoints
- `GET /usage`, `GET /pricing`, `GET /verify-log` (documented in OpenAPI but not required for this completion slice)

## Verification commands

```bash
cd rust
cargo build --locked --bin aigov_audit
cargo test --locked

export GOVAI_LEDGER_DIR=/tmp/govai-ledger-test
export GOVAI_API_KEYS=test-key
export GOVAI_API_KEYS_JSON='{"test-key":"local"}'
export AIGOV_ENVIRONMENT=dev
export AIGOV_POLICY_DIR="$(pwd)"
cargo run --bin aigov_audit --locked
```

## Evaluation gate

The runtime completion package preserves the evaluation gate as an ingest-time and verdict-time control.

Evaluation evidence is accepted only when it satisfies the core policy event contract. The compliance summary derives the final runtime verdict from ledger-authoritative projection state, including failed or missing evaluation evidence.

A run is not considered `VALID` unless required evaluation evidence is present and successful. Failed evaluation evidence contributes to an `INVALID` verdict. Missing evaluation evidence contributes to a `BLOCKED` verdict.

## Human approval gate

The runtime completion package preserves the human approval gate as part of the ledger-authoritative compliance state.

Human approval evidence is evaluated through the core policy contract and represented in the derived projection state. The compliance summary treats missing required approval evidence as a blocking condition.

A run requiring human approval is not considered `VALID` unless the required approval evidence is present and accepted. Missing approval evidence contributes to a `BLOCKED` verdict.

