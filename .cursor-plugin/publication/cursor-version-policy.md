# AIGov Cursor plugin — supported Cursor version policy

## Publication status

This policy applies to the **submission-ready** AIGov Cursor plugin pack. It does **not** imply the plugin is published or approved in Cursor Marketplace.

## Tested baseline (maintainer matrix)

| Cursor channel | Status | Notes |
| --- | --- | --- |
| Current stable desktop | Primary test target | Rules, skills, MCP stdio, Agent |
| Current insiders / beta | Best-effort | Validate MCP panel and skill discovery before listing updates |

Record the exact version used for screenshot capture in the submission portal (for example `2.x.y, macOS 14`).

## Minimum supported (listing copy)

Until Cursor publishes a hard minimum API for plugins, maintainers state:

- **Cursor desktop 0.45+** (or newer stable at submission time) with MCP stdio support and project rules/skills.
- Re-test on each **minor Cursor upgrade** before bumping `plugin.json` `version`.

Update this file and `submission-copy.md` when the tested floor changes.

## Platform notes

| OS | Support level |
| --- | --- |
| macOS | Primary — demo flow and screenshots captured here first |
| Linux | Supported — same MCP argv layout |
| Windows | Best-effort — path separators and `python3` launcher may need local adjustment |

## Compatibility scope

In scope:

- `.mdc` rules under `.cursor-plugin/rules/`
- Agent skills under `.cursor-plugin/skills/*/SKILL.md`
- `govai-local` MCP via `mcp/govai_mcp_server.py`

Out of scope for the plugin pack:

- Hosted AIGov audit API version pinning (see product deployment docs)
- Rust runtime enforcement behaviour

## Upgrade policy for maintainers

1. On Cursor release notes mentioning MCP or rules changes, run `make cursor-plugin-check`.
2. Re-run `publication/demo-flow.md` manually.
3. Bump `plugin.json` `version` patch when only docs/assets change; minor when MCP tool surface changes.
