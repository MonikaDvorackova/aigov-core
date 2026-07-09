# Epistemic readiness runtime implementation audit

Derived epistemic readiness for governance eligibility reconstruction in GovAI Core.

## Architecture

Epistemic readiness is computed by `evaluate_epistemic_readiness_from_export` in `rust/src/epistemic_readiness.rs`. Inputs:

1. An `aigov.audit_export.v1` document (from ledger export or on disk)
2. `EpistemicReadinessOptions` (policy config, optional policy-artifact availability, optional bundle verification signals)

The evaluator calls the existing deterministic replay engine (`replay_audit_export_v1`) and maps replay validation, lineage, policy reference, and optional bundle signals into structured requirements. Status (`ready` / `partial` / `not_ready`) is derived from requirement satisfaction — never written to the ledger.

```
audit export JSON
       │
       ▼
replay_audit_export_v1 ──► ReplayValidationReport + projection
       │
       ▼
build_requirements ──► KnowledgeRequirement[] (sorted)
       │
       ▼
EpistemicReadiness (aigov.epistemic_readiness.v1)
```

Compliance verdict validity (`compliance_verdict_valid`) is explicit and separate from epistemic `status`. A `VALID` run with missing archived policy is `partial`, not `ready`.

## Files changed

| File | Change |
|------|--------|
| `rust/src/epistemic_readiness.rs` | Core types, evaluation, unit tests |
| `rust/src/lib.rs` | Module export |
| `rust/src/audit_export.rs` | Attach derived `epistemic_readiness` at export build |
| `rust/src/bin/epistemic_readiness_once.rs` | Offline JSON evaluator binary |
| `rust/Cargo.toml` | Binary registration |
| `python/aigov_py/epistemic_readiness.py` | Python wrapper |
| `python/aigov_py/cli.py` | `govai epistemic-readiness` command |
| `python/tests/test_epistemic_readiness_cli.py` | CLI smoke test |
| `docs/epistemic-readiness.md` | User-facing guide |

## Derived vs stored

| Artifact | Role |
|----------|------|
| Ledger JSONL | Authoritative evidence (unchanged) |
| `aigov.audit_export.v1` | Canonical export carrier |
| `epistemic_readiness` on export | **Derived** snapshot at export time; recomputable |
| `aigov.epistemic_readiness.v1` CLI output | **Derived** offline view; non-authoritative |
| `ReconstructionConfidence` | Always `non_authoritative: true` |

No mutable knowledge graph. No readiness persistence in Postgres or ledger.

## Validation commands

```bash
cd rust && cargo test --locked
cd .. && python -m pytest -q
python scripts/gate_reports.py
make cursor-plugin-smoke
make release-readiness-check
```

Focused:

```bash
cd rust && cargo test --locked epistemic_readiness
govai epistemic-readiness --export audit_export.json --json
```

## Remaining limitations

- Policy artifact availability is opt-in for offline CLI (`GOVAI_POLICY_ARTIFACT_AVAILABLE`); default offline path is conservative (`false`).
- Bundle verification signals (`unsigned_dependency`, `missing_evidence_reference`) are passed via `EpistemicReadinessOptions`, not yet auto-wired from `verify_audit_export_bundle_once` in the CLI path.
- Scope is governance eligibility reconstruction only — not model behavior, prompts, or embeddings.
- `epistemic_readiness` on export assumes policy was available at export build time.

## Engine independence

All logic lives in GovAI Core (`aigov_audit` crate). No Engine crate, API, or dependency was introduced. Evaluation uses existing replay, projection, and export structures only.

## Evaluation gate

- [x] Epistemic readiness computed from export + replay (no new authoritative store)
- [x] Compliance validity distinguished from epistemic status
- [x] Structured types populated by real evaluation code
- [x] CLI and export integration
- [x] Unit tests for required scenarios
- [x] Deterministic JSON output
- [x] Validation commands documented

## Human approval gate

- [ ] Principal architect review of gap taxonomy vs `docs/architecture/epistemic-model.md`
- [ ] Product decision: wire bundle verifier signals into default CLI path
- [ ] Policy archive integration for automatic `policy_artifact_available` detection
