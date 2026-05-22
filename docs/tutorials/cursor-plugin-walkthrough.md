# Tutorial: Cursor plugin walkthrough

## Audience

Developers using Cursor with the GovAI plugin bundle under **`.cursor-plugin/`**.

## Steps

1. Read **`.cursor-plugin/README.md`** for bundled rules, skills, and MCP tools.
2. Configure the local MCP server using **`.cursor-plugin/mcp.json`**, **`plugin.json`** `mcpServers`, or **`.cursor-plugin/examples/local-config.json`** merged into **`.cursor/mcp.json`**.
3. Run read-only tools first:

   ```bash
   make cursor-plugin-check
   ```

4. In Cursor, invoke **`govai_gate_reports`** (or the documented MCP alias) to validate audit headings.

## Expected outputs

- **`make cursor-plugin-check`** ends with `cursor-plugin-check: OK`.
- MCP tools return JSON with explicit **`ok`** fields for automation-friendly parsing.

## Common failures

- **Forbidden markers in rules** — fix `TODO`-style tokens in `.mdc` rules (validator rejects them).
- **Python path issues** — MCP server relies on repository-relative paths; open the repo root in Cursor.

## Screenshot slot

- MCP panel listing GovAI tools with a successful gate result.

## Marketplace materials

- Publication copy and checklist: [`.cursor-plugin/publication/README.md`](../../.cursor-plugin/publication/README.md)

## Teaching narrative

The plugin accelerates **local consistency** with CI; hosted services remain authoritative for production verdicts.
