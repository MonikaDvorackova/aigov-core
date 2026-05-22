# Cursor plugin integration

## Purpose

Summarize how the GovAI Cursor plugin pack (`.cursor-plugin/`) aligns local agent behaviour with repository gates, and how developer-integrations automation metadata references the same scripts CI uses.

## Integration overview

The plugin includes rules, skills, `plugin.json`, and an optional local MCP bridge. `make cursor-plugin-check` validates the bundle. Developer integrations diagnostics ensure Makefile targets and workflow strings stay aligned with developer integrations CI artifacts.

## Implementation steps

1. Follow `.cursor-plugin/quickstart.md` for first-time setup.
2. Run `make cursor-plugin-check` after editing plugin JSON or MCP definitions.
3. Cross-check `docs/integrations/mcp-integration.md` for protocol-level details.
4. Add automation pack **argv** entries only for commands you expect operators to run manually or in CI.

## Validation

- `make cursor-plugin-check`
- `make developer-integrations`
- `python3 scripts/validate_developer_integrations_manifest.py --json`

## Failure modes

- **Committed local `.cursor/`** — machine-specific; use examples only. Mitigation: follow contributor workflow docs.
- **Plugin/markdown drift** — integration matrix links rot. Mitigation: `make docs-links-strict`.
