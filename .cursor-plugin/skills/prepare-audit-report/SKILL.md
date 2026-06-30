---
name: prepare-audit-report
description: Add docs/reports audit markdown with required CI headings; optional MCP template scaffold and dry-run.
---

# Skill: Prepare required `docs/reports/*.md` audit report

Use this skill when **core enforcement**, **compliance behaviour**, or **governance-affecting** code changes require a traceable audit narrative.

## 1. Confirm need

- If the change touches `python/`, `rust/`, `scripts/`, `.github/workflows/`, `Makefile`, or policy surfaces, assume **a report is required** unless proven documentation-only.

## 2. Create the file

- Add **exactly one** markdown file under `docs/reports/` for the change set (for example `docs/reports/<topic>.md`).
- Include these sections with **exact** level-2 headings (CI enforces a subset across all reports):

  - `## Evaluation gate`
  - `## Human approval gate`
  - `## Risk assessment`
  - `## Rollback plan`

## 3. Optional scaffold (local template)

From repository root:

```bash
python mcp/govai_mcp_server.py govai-generate-audit-report-template --stem my-change-audit --dry-run
python mcp/govai_mcp_server.py govai-generate-audit-report-template --stem my-change-audit
```

Preview with `--dry-run` first (no file write). The non–dry-run command writes `docs/reports/my-change-audit.md` with the required headings and placeholders. Edit the body; **do not** ship empty placeholders in the final PR.

## 4. Validate gates

```bash
python scripts/gate_reports.py
make gate
```

## 5. Branch policy

- Commit the report on your **feature branch**; integrate via **staging → main** per `.cursor-plugin/rules/branch-policy.mdc`.
