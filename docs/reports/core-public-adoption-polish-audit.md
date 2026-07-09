# Core public adoption polish

Documentation and demo fixtures that make GovAI Core easier for external users to understand and try after runtime, packaging, and offline verifier work.

## User-facing changes

| Area | Change |
|------|--------|
| README | New **Try GovAI Core locally** section: venv, runtime start, smoke ingest/export, offline bundle verify |
| Verifier docs | [`docs/signed-audit-export-verifier.md`](../signed-audit-export-verifier.md) — CLI, staged output, crypto vs completeness |
| Demo fixture | `examples/signed-audit-export-bundle/demo.valid.zip` + `trust-demo.json` + snapshot |
| Generator | `scripts/generate_signed_audit_export_bundle_demo.py` — rebuild fixture without runtime |
| Contributor guide | Verifier reason codes, snapshot test workflow, stable `VerificationResult` contract |
| Runtime quickstart | Link to offline bundle verification |

## Files changed

| File | Role |
|------|------|
| `README.md` | Local try-it flow |
| `docs/signed-audit-export-verifier.md` | Verifier documentation |
| `docs/quickstart-runtime.md` | Cross-link to offline verify |
| `docs/project/contributor_workflow.md` | Contributor verifier section |
| `python/aigov_py/audit_export_bundle.py` | Python bundle pack helper (digest parity with Rust) |
| `scripts/generate_signed_audit_export_bundle_demo.py` | Demo bundle generator |
| `examples/signed-audit-export-bundle/*` | Fixture, trust keys, snapshot, README |
| `python/tests/test_signed_audit_export_bundle_demo.py` | Snapshot + generator tests |

## Validation commands

```bash
cd rust && cargo test --locked
cd python && python -m pytest -q
python scripts/gate_reports.py
make cursor-plugin-smoke
make release-readiness-check
```

Optional demo regeneration check:

```bash
python3 scripts/generate_signed_audit_export_bundle_demo.py
python -m pytest python/tests/test_signed_audit_export_bundle_demo.py -q
```

## Remaining risks

- Demo signing key is a **documented test seed** — not for production trust stores.
- README quickstart requires `jq` only for the optional export save step; core flow works without it.
- Verifier binary must be built before first `--bundle` verify (`cargo build --bin verify_audit_export_bundle_once`).
- Snapshot tests depend on Rust verifier output staying aligned with documented contract.

## Evaluation gate

- [x] README quickstart with clean-clone commands (runtime, ingest, export, offline verify)
- [x] Verifier documentation (`overall_status`, staged flags, crypto vs completeness)
- [x] Minimal demo fixture + generator script (Engine-independent)
- [x] Contributor guide for reason codes and snapshot tests
- [x] Single audit report with required headings
- [x] Validation commands listed above pass

## Human approval gate

- [ ] Product/docs review of README placement and Platform doc separation
- [ ] Security acknowledgment that demo trust keys are public test material only
- [ ] Confirm external onboarding paths (Discord, docs index) should link to new verifier doc
