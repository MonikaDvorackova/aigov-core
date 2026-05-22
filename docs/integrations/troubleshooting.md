# Troubleshooting integrations

## Purpose

Give operators and contributors a short triage list for common failures when running GovAI integration checks, developer-integrations validators, or local audit demos.

## Integration overview

Failures cluster into: missing files, invalid JSON, heading gate violations, Makefile target drift, and workflow substring mismatches. Diagnostics encode each as a structured check with `detail` strings for grep-friendly CI logs.

## Implementation steps

1. Run `python3 scripts/developer_integrations_check.py` (without `--json`) for a Markdown table of failing checks.
2. For manifest issues, run `python3 scripts/validate_developer_integrations_manifest.py` and inspect `errors`.
3. For automation packs, run `python3 scripts/validate_automation_pack.py --pack <path>`.
4. For audit service issues, follow `docs/common-errors.md` and `curl` `/ready`.

## Validation

- Re-run `make developer-integrations-platform-check` after fixes to confirm green path.
- `make docs-links-strict` when failures mention missing doc paths.

## Failure modes

- **Gate reports fail** — any `docs/reports/*.md` missing `## Evaluation gate` / `## Human approval gate`. Mitigation: add exact headings on their own lines.
- **Import errors in diagnostics** — validator scripts renamed or deleted. Mitigation: restore paths expected by `scripts/developer_integrations_check.py`.
