# Installation model — AIGov Cursor plugin

**Publication status:** submission-ready; **not live** in Cursor Marketplace.

## Audit conclusion

A **Marketplace-style install that ships only `.cursor-plugin/`** is **not sufficient** for MCP-backed AIGov tools. Rules and skills can load from the plugin subtree, but `govai-local` requires repository-root paths to:

- `mcp/govai_mcp_server.py`
- `python/` (pytest and `aigov_py` standards CLI)
- `scripts/gate_reports.py` and Makefile targets
- `examples/standards/governance_evidence_pack.valid.json`

## Supported installation models

| Model | Rules/skills | MCP tools | Listing recommendation |
| --- | --- | --- | --- |
| **Plugin subtree only** | Yes | No | Document as insufficient for MCP; not the primary submission story |
| **Full repository checkout** | Yes | Yes | **Required** for Marketplace long description and reviewer demo |

Machine-readable definition: [`../installation-model.json`](../installation-model.json).

## Verify locally

```bash
python3 mcp/govai_mcp_server.py installation-check
```

Expect `"installation_mode": "full_repository"` and `"mcp_tools_available": true` when the workspace root is this repository.

## Marketplace copy requirement

`submission-copy.md` must keep the statement that MCP tools require opening the **full AIGov repository** as the Cursor workspace root. Do not imply a plugin-only install runs `govai-local`.

## Future self-contained packaging

Bundling a trimmed MCP server inside `.cursor-plugin/` without `python/` and `scripts/` would require a separate distribution artifact and is **out of scope** for this submission. This package documents the full-repository model instead of misrepresenting plugin-only MCP support.
