# Manual Cursor UI screenshot capture procedure

Real listing screenshots and hero banners cannot be generated headlessly. Use this deterministic procedure after refreshing CLI evidence.

## 1. Prepare reference outputs

```bash
python3 scripts/record_cursor_marketplace_demo_evidence.py
```

This records `assets/capture-evidence/demo-flow-evidence.json` (validation metadata from real MCP CLI runs).

Do **not** generate placeholder banners, watermarked layout tiles, or mock HTML captures.

## 2. Environment

- Cursor stable desktop (record exact version in `cursor-version-policy.md`)
- Full AIGov repository opened as workspace root
- MCP wired from `plugin.json` / `.cursor-plugin/mcp.json`
- Dark theme, 1920×1080 display scaling, notifications hidden

## 3. Capture sequence

| # | Save to | Action |
| --- | --- | --- |
| H | `assets/listing/govai-marketplace-hero-2400x800.png` | Real marketing hero (2400×800) — design or capture; not a composed script output |
| 1 | `assets/listing/govai-cursor-mcp-01-installation-check.png` | Terminal: `installation-check` shows `"ok": true` and `"mcp_tools_available": true` |
| 2 | `assets/listing/govai-cursor-mcp-02-gate-pass.png` | Run `govai_gate_reports`; show `"ok": true` |
| 3 | `assets/listing/govai-cursor-mcp-03-evidence.png` | Run `govai_verify_evidence_pack` on example JSON |
| 4 | `assets/listing/govai-cursor-mcp-04-dry-run.png` | Audit template dry-run with `wrote_file: false` |
| 5 | `assets/listing/govai-cursor-mcp-05-rules.png` | Rules panel with three `.mdc` titles visible |

Compare terminal output against `demo-flow-evidence.json` when verifying captures.

## 4. After capture

1. Update `marketplace-assets.json`: set each captured asset `status` to `committed`.
2. Complete `pre-submit-checklist.md` items `marketplace-hero` and `real-screenshots`.
3. Run `make cursor-marketplace-listing-check` — must pass before portal upload.
