# AIGov Cursor plugin — quickstart

This guide gets you from zero to a **first successful compliance documentation gate** using the AIGov Cursor plugin (rules, skills, and local MCP). Authoritative enforcement remains in the **Rust audit service**, **database policy**, and **CI**; the plugin accelerates consistent local workflows.

## Prerequisites

- Cursor with support for your chosen integration path (rules, skills, MCP as applicable).
- This repository cloned locally.
- Python 3 with the project virtualenv in `python/.venv` (recommended for `pytest` and tooling invoked by MCP).

## Installation in Cursor

1. **Stay on a feature branch** — Follow `rules/branch-policy.mdc`: do not push directly to `main` or `staging`.
2. **Rules** — Copy or symlink `.cursor-plugin/rules/*.mdc` into your workspace `.cursor/rules/` (or your team’s supported rules directory).
3. **Skills** — Copy each `.cursor-plugin/skills/<skill-name>/` folder (each contains `SKILL.md` with YAML frontmatter) into the skills directory your Cursor build discovers (for example `.cursor/skills/govai/`).
4. **Restart Cursor** after changing rules, skills, or MCP configuration.

See also the canonical overview in [README.md](README.md).

## Plugin manifest and MCP

- **Manifest:** [`.cursor-plugin/plugin.json`](plugin.json) — Marketplace-oriented metadata (`name: govai`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, `logo`, `rules`, `skills`, `mcpServers`).
- **Plugin-level MCP:** [`.cursor-plugin/mcp.json`](mcp.json) — defines the `govai-local` stdio server (same shape as the `mcpServers` block in `plugin.json`). Cursor may discover this file when loading the plugin from the repository.
- **Workspace MCP:** For a local `.cursor/mcp.json`, merge **`examples/local-config.json`** or copy **`.cursor/mcp.json.example`** from the repository root.

**Path contract:** `args` use **`mcp/govai_mcp_server.py`** relative to the **repository root**. Open the repo as the workspace root.

**Optional wrapper:** `mcp/run_govai_mcp_stdio.sh` (`command: bash`, `args: ["mcp/run_govai_mcp_stdio.sh"]`). See [`mcp/README.md`](../mcp/README.md). Never tee or log MCP stdout (including to `/tmp`) — stdout must carry JSON-RPC only.

**Clone-friendly copy (no absolute paths, no secrets):** from the repository root:

```bash
mkdir -p .cursor
cp .cursor/mcp.json.example .cursor/mcp.json
```

If you already have a `.cursor/mcp.json`, merge the `govai-local` block from `.cursor-plugin/examples/local-config.json` instead of overwriting. Adjust `command` if your Python is not `python3` on `PATH`.

Security reminder: MCP runs as your user with workspace access; treat configuration as **privileged** in regulated environments.

## First compliance check

Use either MCP tools or the Makefile — both invoke the same underlying scripts where applicable.

**Read-only MCP (examples):**

- `govai-gate-reports` — runs `scripts/gate_reports.py` against `docs/reports/*.md`.
- `govai-check` — runs `python -m pytest` from `python/`.

**Makefile:**

```bash
make gate
```

**Validate the plugin bundle (same as CI):**

```bash
make cursor-plugin-check
```

This runs `scripts/validate_cursor_plugin.py` (manifest, logo, rules, `skills/*/SKILL.md`, MCP config) and `scripts/smoke_cursor_plugin.py` (MCP CLI smoke).

## Evidence pack verification

1. Start from `examples/standards/governance_evidence_pack.valid.json` or your own pack path **inside the repo** (path constraints apply).
2. Invoke **`govai-verify-evidence-pack`** via MCP with the relative path, or use the Python CLI documented in the main repository docs.

Confirm the tool returns structured JSON with `ok: true` before you rely on the pack in a review or customer deliverable.

## Audit report generation

1. Use the **`govai-generate-audit-report-template`** MCP tool (or CLI) with `dry_run: true` first to preview headings and structure.
2. Write the final report under `docs/reports/<name>.md` including at least:
   - `## Evaluation gate`
   - `## Human approval gate`
3. Run `python scripts/gate_reports.py` or `make gate` to confirm CI compatibility.

Skill reference: `skills/prepare-audit-report/SKILL.md`.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| MCP server not starting | Python on `PATH`, correct repo root in workspace, `args` path to `mcp/govai_mcp_server.py`, Cursor restarted after edits. |
| `govai-check` fails | Activate `python/.venv`, install dev dependencies, run `python -m pytest` manually for full trace. |
| Gate reports fail | Each `docs/reports/*.md` must contain the exact headings `## Evaluation gate` and `## Human approval gate` (see `scripts/gate_reports.py`). |
| Evidence path rejected | Use a path under the repository root; symlinks and `..` escapes are constrained by design. |

Deeper operational context: [../docs/troubleshooting.md](../docs/troubleshooting.md) and [.cursor-plugin/README.md](README.md).

## Next steps

- Personas and workflows: [use-cases.md](use-cases.md).
- Commercial packaging and pricing: [../docs/commercial/pricing.md](../docs/commercial/pricing.md).
