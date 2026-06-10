# AIGov Cursor plugin — marketplace and distribution assets

This directory holds visual assets and manifests for the AIGov Cursor Marketplace submission package.

**Approved brand source:** `dashboard/brand/aigov-mark.ico`

**Publication status:** internally usable; documentation-ready; listing media committed; **not live** in Cursor Marketplace — see [`../publication/status.md`](../publication/status.md).

| Asset | File | Status |
| --- | --- | --- |
| Manifest logo | `logo.png` | **Committed** — 48×48 ICO frame on 512×512 canvas via `scripts/sync_cursor_marketplace_brand_from_ico.sh` |
| Marketplace hero | `listing/govai-marketplace-hero-2400x800.png` | **Committed** — unchanged ICO mark on dark background |
| Listing screenshots | `listing/govai-cursor-mcp-*.png` | **Committed** |
| Brand derivation record | `brand-derivation.json` | SHA-256 hashes for ICO-derived logo and hero |
| Demo-flow evidence | `capture-evidence/demo-flow-evidence.json` | **Committed** |
| Asset manifest | `marketplace-assets.json` | Machine-readable list for CI validation |

**Forbidden:** generated wordmarks, glow logos, SVG pipelines, `icon-512.png`, bracket-only substitutes, or any logo not traced to `aigov-mark.ico`.

Regenerate logo and hero after ICO edits:

```bash
./scripts/sync_cursor_marketplace_brand_from_ico.sh
```

Validation:

- `make cursor-plugin-check` — plugin layout, brand derivation, publication docs.
- `make cursor-marketplace-listing-check` — all committed listing assets on disk.
