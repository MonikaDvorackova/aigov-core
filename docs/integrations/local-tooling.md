# Local tooling

## Purpose

List stdlib-only scripts and Makefile targets developers run locally for developer-integrations health: diagnostics, manifest validation, automation pack validation, and Markdown summary generation—without network I/O in validators.

## Integration overview

Scripts live under `scripts/` and use `python3` from the shell. The Makefile exposes `developer-integrations`, `developer-integrations-manifest`, `automation-pack`, `automation-pack-summary`, and aggregate `developer-integrations-platform-check`. Outputs are deterministic JSON (with `--json`) or Markdown suitable for CI artifacts.

## Implementation steps

1. From repo root, run `make developer-integrations-platform-check` before pushing integration changes.
2. For JSON snapshots: `python3 scripts/developer_integrations_check.py --json > /tmp/out.json` (do not commit unless CI requires).
3. Install the Python venv only when using `govai` or pytest; validators do not require venv.
4. Read `examples/integrations/README.md` for shell drivers.

## Validation

- `make developer-integrations-platform-check` or the individual targets listed in `docs/integrations/developer-integrations-manifest.json` under `required_checks`
- `python3 scripts/validate_developer_integrations_manifest.py --json`
- `examples/integrations/run-developer-integrations-check.sh`

## Failure modes

- **Stale Python** — require 3.10+ per project standards. Mitigation: pin in contributor docs.
- **Running from subdirectories** — relative paths in packs assume repo root. Mitigation: document `cwd` in team playbooks.
