# Screenshot plan (Cursor Marketplace)

Capture **1920×1080** stills with dark theme. Redact personal notifications and secrets.

**Publication status:** plugin is **not live** in Cursor Marketplace. Hero and screenshots are **missing** until real captures are committed.

## Ordered real captures (portal upload)

Save under `assets/listing/` per [`manual-capture-procedure.md`](manual-capture-procedure.md).

| # | Filename | Scene |
| --- | --- | --- |
| H | `govai-marketplace-hero-2400x800.png` | Marketing hero banner (2400×800) |
| 1 | `govai-cursor-mcp-01-installation-check.png` | Terminal: `installation-check` shows `"ok": true` and `"mcp_tools_available": true` |
| 2 | `govai-cursor-mcp-02-gate-pass.png` | `govai_gate_reports` output with `"ok": true` |
| 3 | `govai-cursor-mcp-03-evidence.png` | `govai_verify_evidence_pack` on example JSON |
| 4 | `govai-cursor-mcp-04-dry-run.png` | Audit template dry-run: `wrote_file: false` and preview body |
| 5 | `govai-cursor-mcp-05-rules.png` | Rules panel showing branch policy, audit report, compliance gate `.mdc` titles |

CLI reference output: `assets/capture-evidence/demo-flow-evidence.json`.

## Alt text guidance

Describe the **governance action** (gate pass, evidence validation), not Cursor chrome jargon.

## Optional motion

If Cursor requests video: 720p, ≤60s, follow `demo-flow.md`. Status `not_required` in `marketplace-assets.json`.
