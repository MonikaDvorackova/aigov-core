# CLI reference

The `govai` command is shipped with the **`aigov-py`** Python package in this repository (`python/pyproject.toml`, implementation `python/aigov_py/cli.py`). Install from PyPI (pin the version in CI to match your action pin):

```bash
python -m pip install "aigov-py==0.2.1"
```

Run `govai --help` and `govai <command> --help` for the exact flags for your installed version.

```docs
preset: cli-catalog
```

## Global flags (root parser)

| Flag | Env / config | Purpose |
|------|----------------|--------|
| `--version` / `-V` | — | Print package version and exit. |
| `--config` | `.govai/config.json` or `GOVAI_CONFIG` | Path to JSON config. |
| `--audit-base-url` | `GOVAI_AUDIT_BASE_URL` (and config) | Audit HTTP base URL. |
| `--api-key` | `GOVAI_API_KEY` (and config) | Bearer token for gated audit routes. |
| `--project` | `GOVAI_PROJECT` / `X_GOVAI_PROJECT` | Sets `X-GovAI-Project` header (**metadata only**; does not select tenant). |
| `--timeout` | `GOVAI_TIMEOUT_SEC` (default 30) | HTTP timeout in seconds. |
| `--compact-json` | — | Single-line JSON for selected commands (for example `compliance-summary`). |

## Exit codes (`python/aigov_py/cli_exit.py`)

| Code | Constant | Meaning |
|------|----------|---------|
| 0 | `EX_OK` | Success. For `govai check` / `verify-evidence-pack`, success implies **VALID** verdict when checking verdict. |
| 1 | `EX_ERR` | Transport, HTTP failure, parse failure, digest/export mismatch, or unexpected error. |
| 2 | `EX_INVALID` | Compliance verdict **INVALID**. |
| 3 | `EX_BLOCKED` | Compliance verdict **BLOCKED**. |
| 4 | `EX_USAGE` | CLI usage error (including argparse errors). |

**Note:** `govai check` help text documents exit **4** as “usage”; infrastructure failures use exit **1** (see parser docstrings in `cli.py`).

## `govai check`

Queries **`GET /compliance-summary`** for the run and exits **0** only if the verdict is **`VALID`**.

- **Positional or `--run-id`:** run UUID (also `GOVAI_RUN_ID` / `RUN_ID`).
- **`--verify-artifacts <dir>`:** After verdict check, require `evidence_digest_manifest.json` under `dir` to match hosted **`GET /bundle-hash`** (artefact continuity).

Does **not** alone prove full CI artefact binding; for release gates prefer **`verify-evidence-pack`** (and the composite GitHub Action). See [`github-action.md`](github-action.md).

## `govai verify-evidence-pack`

Hosted gate for CI artefacts:

- Requires **`--path <dir>`** with `evidence_digest_manifest.json` and `<run_id>.json`.
- Compares manifest digest to hosted **`GET /bundle-hash`** (`events_content_sha256`).
- **`--require-export`:** fail if **`GET /api/export/:run_id`** cross-check cannot be performed or disagrees with `/bundle-hash`.
- **`--artifact-file`:** optional on-disk promoted model file; verifies SHA256 against bundle payload when provided.

## Evidence pack generation

| Command | Purpose |
|---------|---------|
| `govai evidence-pack init` | Writes `<run_id>.json` and `evidence_digest_manifest.json` under `--out` (default `evidence_pack/`). `--run-id` optional (CI-deterministic on GitHub Actions; else UUID). `--force` to overwrite. |

Related:

- **`govai submit-evidence-pack`** — POST every event from `<dir>/<run_id>.json` to **`POST /evidence`**.
- **`govai preflight`** — Local validation and optional `--with-submit` against the audit service (see `--help`).

## Report generation

| Command | Purpose |
|---------|---------|
| `govai report` | Renders `docs/reports/<run_id>.md` from evidence / bundle inputs (see `govai report --help`). |

## Other documented customer paths (non-exhaustive)

The CLI exposes additional subcommands (`init`, `export-run`, `compliance-summary`, `usage`, `discovery`, `policy`, `standards`, …). Only document commands you use; this page lists those explicitly tied to public docs and CI gates in this repository.

## CI integration

- Composite action and pins: [`github-action.md`](github-action.md)
- Artefact-bound gate: `submit-evidence-pack` then `verify-evidence-pack` with **`--require-export`** by default in the published action.

## Related

- Quickstart: [`customer-quickstart.md`](customer-quickstart.md), [`quickstart-5min.md`](quickstart-5min.md)
- Hosted deployment: [`hosted-backend-deployment.md`](hosted-backend-deployment.md)
- HTTP contract: [`api-reference.md`](api-reference.md)
