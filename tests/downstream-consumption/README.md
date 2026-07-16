# Downstream consumption smoke tests

These checks prove AIGov Core can be consumed as an **external dependency**, not only when built inside this repository.

## What is validated

| Consumer | Mechanism | Public surface |
|----------|-----------|----------------|
| `rust-consumer/` | Separate crate with `path = "../../../rust"` | `audit_export_verification`, `policy`, `replay_validation` |
| `scripts/downstream_python_consumption_smoke.py` | Fresh venv + `pip install ./python` (non-editable) | `govai` package imports, `govai` CLI, standards + bundle verifier |

## Why these exist

Packaging and public API regressions are easy to miss when all tests live in the main crate or an editable Python install. Downstream smokes fail CI when:

- the Rust library no longer compiles for external crates
- public modules are removed or renamed
- the Python wheel/sdist install breaks imports or CLI entrypoints

## Run locally

From the repository root:

```bash
make downstream-consumption-smoke
```

The Makefile builds `verify_audit_export_bundle_once` before the Python smoke (required for `govai verify-evidence-pack --bundle`).

Or individually:

```bash
cd tests/downstream-consumption/rust-consumer && cargo test --locked
python3 scripts/downstream_python_consumption_smoke.py
```

No crates.io, PyPI, or running audit HTTP server is required.
