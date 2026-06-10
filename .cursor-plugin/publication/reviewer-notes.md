# Cursor Marketplace — reviewer notes (AIGov)

For Cursor marketplace reviewers and internal release owners. This plugin is **submission-ready** in this repository but **not live** in Cursor Marketplace.

## Repository layout expectation

Run `python3 mcp/govai_mcp_server.py installation-check` first; expect `full_repository` when this repo is the workspace root.

Reviewers should evaluate the plugin against a **full repository checkout** opened as the Cursor workspace root. The workspace must contain:

- `.cursor-plugin/` — manifest, rules, skills, publication package
- `mcp/govai_mcp_server.py` — stdio MCP bridge
- `python/` — pytest and evidence validation dependencies
- `scripts/` — gate and validation scripts invoked by MCP tools

A Marketplace install that exposes **only** `.cursor-plugin/` without `mcp/` cannot run `govai-local` tools; rules and skills still apply.

## Security and execution model

- MCP runs **locally** as the developer OS user via `python3 mcp/govai_mcp_server.py mcp-stdio`.
- Default tool paths use **explicit argv lists**, **timeouts**, and **no outbound network** in read-only diagnostics.
- Only `govai_generate_audit_report_template` writes disk by default; **`dry_run: true`** previews without writing.
- Evidence pack paths are constrained to the repository root.

## Recommended review order

1. Read `publication/status.md` — confirms not live / not approved.
2. Skim `plugin.json` and `.cursor-plugin/mcp.json` — `govai-local` stdio definition.
3. Run `make cursor-plugin-check` from repository root (validate + MCP smoke).
4. Follow `demo-flow.md` in Cursor with MCP connected.
5. Confirm `submission-copy.md` limitations match observed behaviour.

## Tool surface (read vs write)

| Tool | Write? | Notes |
| --- | --- | --- |
| `govai_check` | No | Runs `python -m pytest` from `python/`. |
| `govai_verify_evidence_pack` | No | Offline standards validation. |
| `govai_gate_reports` | No | `scripts/gate_reports.py`. |
| `govai_make_gate` | No | `make gate` (heavier). |
| `govai_generate_audit_report_template` | Yes | Creates `docs/reports/<stem>.md`; supports dry-run. |

## Known limitations for review

- **Not** a certified compliance product; CI and hosted audit services remain authoritative.
- **Linux/macOS-first** examples; Windows may need path adjustments in local MCP config.
- **Minimal stdio MCP** — not a full remote MCP SaaS deployment.
- Full `make gate` may exceed default MCP timeouts on very large trees.

## Privacy and telemetry

- Default MCP tools do **not** add vendor telemetry.
- No secrets are required for read-only smoke tools.
- Hosted AIGov API keys are out of scope for the local plugin pack.

## Contact during review

See `support-and-contact.md` for issue tracker and maintainer contacts.
