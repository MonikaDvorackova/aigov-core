# Core OSS Normalization

## Summary

Normalized repository identity documentation so **this tree presents as GovAI Core** — the open-source ledger-authoritative audit runtime — rather than as the proprietary GovAI Platform repository pointing at an external `govai-core` copy.

Documentation now states core scope, platform exclusions, contributor invariants, and correct clone URLs (`MonikaDvorackova/govai-core`). No runtime semantics were changed.

## Evaluation gate

Evaluation evidence remains represented as **ledger-authoritative evidence** (`evaluation_reported` and related event types). It is ingested append-only and contributes to **deterministic compliance summary** verdicts via ledger projection (`evaluation_passed` drives **INVALID** when false). Contributors must not introduce trace-derived or side-channel verdict overrides on `GET /compliance-summary`.

## Human approval gate

Human approval evidence remains represented as **ledger-authoritative evidence** (`human_approved`, `risk_reviewed`, and related types). It contributes to **deterministic compliance summary** verdicts through projection state (reject decisions and promotion prerequisites). Contributors must not bypass approval semantics with implicit tenant fallbacks or non-ledger verdict sources.

## Repository scope

| Layer | Classification |
|-------|----------------|
| `rust/src/govai_api.rs` mounted routes | **GovAI Core** — authoritative integrator surface |
| `docs/quickstart-runtime.md`, runtime examples | **GovAI Core** — adoption path |
| `docs/hosted/`, `docs/billing/`, `dashboard/` | **Platform reference** — not core runtime |
| `OPEN_SOURCE_SCOPE.md` (prior) | **Misleading residue** — stated this repo was platform; **fixed** |
| README opening (prior) | **Misleading residue** — claimed private platform; **fixed** |
| `aigov-compliance-engine` clone URLs | **Misleading residue** — **fixed** to `govai-core` |
| `kovali.ai` schema `$id` | **Misleading residue** — **fixed** to GitHub schema URL |
| `LICENSE` (proprietary text) | **Manual follow-up** — file not changed in this PR; maintainers must align license text with OSS intent via separate legal/repo settings change |

## Changes made

- **README.md** — GovAI Core positioning, scope table, platform docs labeled reference-only; removed pricing/billing quickstart blocks; fixed clone and composite action repo names.
- **OPEN_SOURCE_SCOPE.md** — Rewritten for in-repo GovAI Core scope and invariants.
- **CONTRIBUTING.md**, **GOVERNANCE.md**, **SECURITY.md**, **CODE_OF_CONDUCT.md** — Core OSS scope and technical invariants.
- **docs/project/local_development.md** — Clone URL.
- **docs/schemas/aigov.audit_export.v1.schema.json** — `$id` without Kovali branding.
- **examples/adoption/github-actions-ci-gate/** — Action reference `MonikaDvorackova/govai-core@v1`.
- **python/aigov_py/experiments/real_world_ci_runner.py** — Git dependency URL.

## Verification

```bash
make gate
make core-runtime-examples-check
cd rust && cargo build --locked --bin aigov_audit && cargo test --locked
```

All commands expected to pass (no Rust source changes in this PR).
