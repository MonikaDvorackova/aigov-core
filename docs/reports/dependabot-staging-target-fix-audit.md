# Dependabot staging target audit

**Date:** 2026-06-20  
**Repository:** [govai-core](https://github.com/MonikaDvorackova/govai-core)  
**Issue:** Dependabot opened Cargo dependency pull requests against `main` instead of `staging`.

## Root cause

`.github/dependabot.yml` contained **invalid YAML** for the Cargo update block:

```yaml
  - package-ecosystem: cargo
    directory: /rust
target-branch: stagingtarget-branch: staging
    schedule:
```

Two defects on the same line:

1. **Wrong indentation** — `target-branch` was at the document root (column 0), not nested under the Cargo `updates` entry. Dependabot therefore did not apply `target-branch` to Cargo updates and used the repository default branch (`main`).
2. **Corrupted value** — the line concatenated two keys (`stagingtarget-branch: staging`), which makes the file **unparseable** by strict YAML parsers (`yaml.safe_load` fails at column 36).

The Python (`pip`) block was correctly configured with `target-branch: staging` at the proper indentation, which explains why only **Cargo** Dependabot PRs targeted `main`.

### Evidence

| Source | Finding |
|--------|---------|
| `.github/dependabot.yml` (before fix) | Malformed line 5 as above |
| `python3 -c "yaml.safe_load(...)"` | `mapping values are not allowed here` at line 5, column 36 |
| `gh pr list --author app/dependabot` | PR #116 (`zip`), #117 (`rand`) — `baseRefName: main`, Cargo paths |
| `.github/workflows/pr-branch-policy.yml` | Blocks non-staging PRs to `main` but does **not** change Dependabot base branch selection |
| GitHub repository settings / rulesets | **Not investigated via API** — Dependabot v2 `target-branch` is defined in `.github/dependabot.yml`; no in-repo Renovate or other dependency-bot automation found |

### What does **not** override Dependabot targets

- **Branch protection / rulesets** — control merge requirements, not which base branch Dependabot selects.
- **`pr-branch-policy.yml`** — fails PRs that target `main` from non-`staging` heads; Dependabot still *opens* against `main` when config is wrong.
- **No Renovate** or alternate dependency-update bots found in `.github/`.

## Changes made

| File | Change |
|------|--------|
| `.github/dependabot.yml` | Fixed YAML: both `cargo` and `pip` blocks include properly indented `target-branch: staging` |
| `scripts/check_dependabot_config.py` | **Added** — validates YAML, rejects root-level/duplicated `target-branch`, requires `staging` on every `updates` entry |
| `python/tests/test_dependabot_config.py` | **Added** — regression tests for validator and config |
| `Makefile` | **Added** `dependabot-config-check` target |
| `.github/workflows/supply-chain-audit.yml` | **Added** `dependabot-config` job; installs `pip install -e ".[dev]"` before `make dependabot-config-check` |
| `python/pyproject.toml` | **Added** `PyYAML>=6.0.0` to `[project.optional-dependencies].dev` (also present in main deps for runtime) |

## CI dependency fix (follow-up)

**Symptom:** `dependabot-config` job failed in PR #118 with `PyYAML is required (pip install pyyaml)`.

**Cause:** `scripts/check_dependabot_config.py` uses `yaml.safe_load`, but the `dependabot-config` job ran `make dependabot-config-check` on a bare GitHub Actions Python 3.11 image without installing project dependencies.

**Fix:** Align with the `pip-audit` job pattern — create a venv, `pip install -e ".[dev]"`, activate, then run `make dependabot-config-check`. List `PyYAML` explicitly under `dev` optional dependencies for CI/tooling clarity.

## Validation performed

```bash
# CI-equivalent (clean venv)
cd python && python -m venv .venv && . .venv/bin/activate
pip install -U pip && pip install -e ".[dev]"
cd .. && make dependabot-config-check
# dependabot-config-check: OK — 2 update block(s) target 'staging' (cargo, pip)

cd python && . .venv/bin/activate && pytest tests/test_dependabot_config.py -q
# 2 passed
```

**Pre-fix YAML parse:** fails with `mapping values are not allowed here` (line 5).  
**Post-fix:** parses cleanly; both ecosystems assert `target-branch: staging`.

## Follow-up (manual)

1. **Close or retarget** open Dependabot PRs #116 and #117 (currently against `main`); Dependabot will open new PRs against `staging` after this config merges.
2. Confirm no duplicate Dependabot configuration exists in GitHub **Settings → Code security → Dependabot** (repository UI); file-based v2 config is authoritative when present.

## Evaluation gate

Status: pass (configuration and CI guard restored).

## Human approval gate

Status: pending maintainer review.

Reviewer: Monika Dvořáčková
