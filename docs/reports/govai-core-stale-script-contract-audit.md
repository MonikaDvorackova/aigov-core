# GovAI Core stale script contract audit

## Summary

GovAI Core ships fifteen Python utilities under `scripts/`. The repository retained pytest modules, Makefile targets, and workflow steps copied from the larger proprietary platform repository. Those references pointed at scripts that never existed in GovAI Core history, causing CI `FileNotFoundError` failures during collection and execution.

## Root cause

Open-core split left platform-only validators (commercial, hosted, regulatory, release engineering, and similar) referenced by tests and automation, but without corresponding implementations under `scripts/` in this repository.

## Change

- Removed pytest files that import or execute missing `scripts/*.py` entrypoints.
- Retained tests for real GovAI Core scripts and runtime/Python modules.
- Replaced Makefile platform targets with aggregates that call only scripts present in this repository.
- Slimmed `oss-developer-experience` workflow to cursor plugin, public SDK packages, gate, and core readiness checks.
- Aligned `public_sdk_packages_check.py` Makefile expectations with GovAI Core (`oss-ecosystem-check` only).
- Removed the Cursor MCP `govai_validate_functions_v2_pack` tool and smoke case (validator script ships in the platform repository).

Platform-only automation remains in the proprietary platform repository.

## Evaluation gate

GovAI Core CI still runs documentation gate (`gate_reports.py`), Rust checks, governance standards pytest, portable artifact smoke, core runtime contract scripts, public SDK package validation, and cursor plugin validate/smoke. No enforcement paths were removed—only references to non-existent scripts were deleted.

## Human approval gate

No human approval workflow was weakened. Audit report heading requirements and compliance semantics are unchanged.
