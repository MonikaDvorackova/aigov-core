# Downstream consumption smoke tests audit

## Summary

Adds minimal downstream consumers that install GovAI Core as an external dependency (Rust path crate + non-editable Python pip install) and run offline smoke checks in CI on pull requests. Closes #48 and #49.

## Files changed

| Path | Change |
|------|--------|
| `tests/downstream-consumption/rust-consumer/Cargo.toml` | External crate depending on `aigov_audit` via `path = "../../../rust"` |
| `tests/downstream-consumption/rust-consumer/Cargo.lock` | Locked dependency graph for reproducible downstream builds |
| `tests/downstream-consumption/rust-consumer/tests/smoke.rs` | Smoke tests for verifier, policy, and export schema public APIs |
| `scripts/downstream_python_consumption_smoke.py` | Fresh venv, `pip install ./python`, import + CLI smokes |
| `tests/downstream-consumption/README.md` | What/why/how for contributors |
| `Makefile` | `downstream-consumption-smoke` target |
| `.github/workflows/govai-ci.yml` | Downstream Rust and Python steps on PRs |
| `docs/project/contributor_workflow.md` | Local validation command |

## Architecture

```
govai-core/
  rust/                          # aigov_audit library (published surface)
  python/                        # aigov-py package
  tests/downstream-consumption/
    rust-consumer/               # separate Cargo project (path dependency)
  scripts/downstream_python_consumption_smoke.py
```

The Rust consumer compiles outside `rust/` and imports `audit_export_verification`, `policy`, and `replay_validation`. The Python script creates a temporary venv, installs from `./python` without `-e`, imports `govai` and `aigov_py.standards.cli`, then runs `govai --help`, `govai standards validate-evidence-pack`, and `govai verify-evidence-pack --bundle` against committed demo fixtures.

## Validation commands

```bash
make downstream-consumption-smoke
cd rust && cargo test --locked
cd python && python -m pytest -q
python3 scripts/gate_reports.py
make cursor-plugin-smoke
make release-readiness-check
```

## Test results

| Check | Result |
|-------|--------|
| `make downstream-consumption-smoke` | **PASS** (3 Rust tests + Python venv install/CLI) |
| `cargo test --locked` | **PASS** |
| `python -m pytest -q` | **PASS** (420 passed, 2 skipped) |
| `python3 scripts/gate_reports.py` | **PASS** |
| `make cursor-plugin-smoke` | **PASS** |
| `make release-readiness-check` | **PASS** |

## CI integration

Job `govai-core-portable` in `.github/workflows/govai-ci.yml` runs on pull requests to `main` and `staging`, after the main Rust test step:

1. `cd tests/downstream-consumption/rust-consumer && cargo test --locked`
2. `python3 scripts/downstream_python_consumption_smoke.py`

No crates.io or PyPI publish steps are added.

## Remaining limitations

- Rust consumer uses a **path** dependency, not a git tag or crates.io release.
- Python smoke uses a local directory install, not PyPI.
- Smokes are offline; they do not start the audit HTTP runtime.
- Bundle verification depends on committed fixtures under `examples/signed-audit-export-bundle/` and the `verify_audit_export_bundle_once` binary (built in `make downstream-consumption-smoke` and CI).

## Core remains Engine-independent

Consumers use only the `aigov_audit` Rust library and `aigov-py` Python package from this repository. No imports, paths, or CI steps reference GovAI Platform or `aigov-compliance-engine`.

## Evaluation gate

- [x] Rust downstream consumer compiles outside the main crate
- [x] Rust smoke imports and exercises public verifier, policy, and export APIs
- [x] Python smoke installs from `./python` in a fresh venv (non-editable)
- [x] Python imports and CLI commands succeed
- [x] Signed demo bundle verifies via `govai verify-evidence-pack --bundle`
- [x] `make downstream-consumption-smoke` runs both consumers
- [x] CI runs downstream smokes on pull requests
- [x] Core remains Engine-independent

## Human approval gate

- [ ] Maintainer confirms path-dependency smoke is sufficient until git-tag consumer is added
- [ ] Review fixture paths if `examples/signed-audit-export-bundle/` layout changes
