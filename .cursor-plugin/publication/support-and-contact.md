# AIGov Cursor plugin — support and contact

## Publication status

The AIGov Cursor plugin is **internally usable** from this repository and **submission-ready**, but it is **not live** in Cursor Marketplace and has **not** received listing approval.

## Community support (default)

| Channel | URL / address | Scope |
| --- | --- | --- |
| GitHub issues | https://github.com/MonikaDvorackova/aigov-compliance-engine/issues | Bug reports, docs gaps, MCP wiring questions |
| Repository docs | `.cursor-plugin/quickstart.md`, `.cursor-plugin/README.md` | Install, MCP, first gate |
| Product site | https://govbase.dev | Hosted AIGov product (separate from Marketplace plugin SLA) |
| General contact | hello@govbase.dev | Routing to maintainers |

**No SLA** applies to Marketplace or OSS plugin installs unless covered by a separate commercial agreement.

## Enterprise / hosted customers

Hosted audit, billing, and production support are governed by customer contracts and `docs/commercial/support-and-sla.md`. The Cursor plugin is a **local developer accelerator**, not the hosted service support channel.

## What to include in support requests

- Cursor version (see `cursor-version-policy.md`)
- OS and Python version (`python3 --version`)
- Output of `make cursor-plugin-check` (redact secrets)
- Whether the workspace root is the full AIGov repository checkout
- MCP tool name and structured JSON response (truncate large stdout)

## Security issues

Report sensitive findings through the repository’s documented security contact process. Do not paste production API keys or customer evidence packs into public issues.
