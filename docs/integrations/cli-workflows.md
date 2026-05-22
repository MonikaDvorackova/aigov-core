# CLI workflows (govai and Make)

## Purpose

Document how developers use the **`govai`** CLI (under `python/`) and root **`Makefile`** targets for local evidence posting, compliance checks, and developer-integrations validation.

## Integration overview

The Python package exposes `govai check` and related commands with documented exit codes. The Makefile wraps stdlib scripts (`scripts/*.py`) so shells and CI share one contract. Developer-integrations targets (`developer-integrations-manifest`, `automation-pack`, etc.) require **Python 3** on `PATH` but not the project venv.

## Implementation steps

1. Install the editable package per `docs/project/local_development.md`.
2. Export `GOVAI_AUDIT_BASE_URL`, `GOVAI_API_KEY`, and optional `GOVAI_PROJECT` for live calls.
3. For documentation-only validation, run `make developer-integrations-platform-check` from the repository root without starting Docker.
4. Use `examples/integrations/sample-cli-workflow.sh` as a copy-paste skeleton.

## Validation

- `python3 scripts/developer_integrations_check.py --json`
- `make developer-integrations-manifest`
- `examples/integrations/run-developer-integrations-check.sh`

## Failure modes

- **Wrong working directory** — Makefile paths assume repo root. Mitigation: `cd` to root before `make`.
- **Venv confusion** — stdlib scripts use `python3` system-wide; `govai` needs the venv. Mitigation: document which command needs which environment in team runbooks.
