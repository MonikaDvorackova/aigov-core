---
name: fix-compliance-gate
description: Diagnose and fix failing governance gates (pytest, Rust, gate_reports, make gate) with minimal scoped changes.
---

# Skill: Fix AIGov compliance gate failures

Use this skill when **`python scripts/gate_reports.py`**, **`make gate`**, **pytest**, **Rust tests**, or **artifact-bound CI** fails after local edits.

## 1. Capture failure context

- Re-run from repository root: `python -m pytest`, `cargo test --manifest-path rust/Cargo.toml`, `python scripts/gate_reports.py`, `make gate`.
- Save the **first failing command** output verbatim (stdout + stderr).

## 2. Classify the failure

| Symptom | Likely cause | Next step |
|--------|----------------|-----------|
| `gate FAIL; missing required sections` | `docs/reports/*.md` missing `## Evaluation gate` or `## Human approval gate` | Open each listed file; add exact headings on their own lines. |
| pytest import / collection errors | Wrong cwd, missing venv, or broken package install | Run from `python/` with `.venv` activated (`pip install -e ".[dev]"`). |
| Rust compile or test failure | Lockfile drift or code regression | Read compiler/test output; fix only the regression introduced by the current change set. |
| `make gate` differs from direct `gate_reports.py` | Should not happen (`make gate` calls the script) | Confirm you are at repo root; compare `Makefile` `gate` target. |

## 3. Fix with minimal scope

- Prefer **smallest** edits that restore green: do not refactor unrelated modules.
- **Do not** weaken hosted compliance semantics, verdict mapping, or remove required CI jobs to “get green”.
- If the failure is **documentation-only**, add or fix headings in the relevant `docs/reports/*.md` file for this change set.

## 4. Re-verify

Run the full sequence again:

1. `python -m pytest`
2. `cargo test --manifest-path rust/Cargo.toml`
3. `python scripts/gate_reports.py`
4. `make gate`

## 5. Escalation

If failures persist in **Rust runtime enforcement** or **database migrations**, stop and ask for explicit owner approval before changing those areas (they are out of scope for typical plugin or docs work).
