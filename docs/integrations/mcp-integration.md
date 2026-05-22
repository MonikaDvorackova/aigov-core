# MCP integration

## Purpose

Explain how the Model Context Protocol (MCP) bridges local agents to GovAI documentation and validation scripts, aligned with the checked-in Cursor plugin pack and **no** silent changes to hosted enforcement.

## Integration overview

The repository ships MCP configuration examples under `.cursor-plugin/` and `mcp/`. MCP tools surface read-only or local-validation operations; production audit, ledger, and billing remain server-side. Developer integrations automation packs can list MCP-related commands as **documentation** of argv shape—validators do not execute them.

## Implementation steps

1. Read `.cursor-plugin/quickstart.md` for installation and security boundaries.
2. Merge `mcp.json` examples without committing secrets or absolute user paths.
3. Point agents at `make developer-integrations-platform-check` or individual Python validators for deterministic JSON.
4. Keep `GOVAI_API_KEY` out of MCP server static config; use environment injection from the IDE.

## Validation

- `make cursor-plugin-check`
- `python3 scripts/developer_integrations_check.py --json`
- `docs/integrations/cursor-plugin.md` for overlap with IDE packaging

## Failure modes

- **Over-trusting local tools** — MCP success does not imply `VALID` verdict on hosted runs. Mitigation: treat MCP output as pre-flight only.
- **Stale plugin paths** — moving scripts without updating automation pack metadata breaks artifact checks. Mitigation: run `make automation-pack` after edits.
