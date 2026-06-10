# AIGov Cursor plugin — publication status

Authoritative marketplace readiness statement. **Does not** claim Cursor approval or an approved Marketplace listing.

## Current state

| Layer | Status | Meaning |
| --- | --- | --- |
| **Internally usable** | Ready | Full repository clone; `make cursor-plugin-check` passes; rules, skills, and MCP tools work when workspace root is the repo. |
| **Documentation package** | Ready | Portal copy, installation model, demo-flow evidence, capture procedure, and checklists are in-repo. |
| **Listing media** | **Committed** | Logo, hero, and five screenshots committed. Approved brand source: `dashboard/brand/aigov-mark.ico`. Logo and hero derived via `scripts/sync_cursor_marketplace_brand_from_ico.sh` without mark scaling or redraw. |
| **Cursor Marketplace** | **Not live** | **Not published**, **not approved**, no approved listing as of `plugin.json` `version`. |

## Approved brand source

**`dashboard/brand/aigov-mark.ico`** is the approved canonical AIGov mark. Generated wordmarks, glow logos, SVG logo pipelines, and `icon-512.png` substitutes remain forbidden.

| Derived asset | Path | Source |
| --- | --- | --- |
| Manifest logo | `assets/logo.png` | 48×48 ICO frame on 512×512 canvas (no scaling) |
| Marketplace hero | `assets/listing/govai-marketplace-hero-2400x800.png` | Unchanged ICO mark on dark background |

Hashes: `.cursor-plugin/assets/brand-derivation.json`

## Installation model (audit)

| Install shape | Rules/skills | MCP tools |
| --- | --- | --- |
| Plugin subtree only | Yes | **No** — paths to `mcp/`, `python/`, `scripts/` missing |
| Full repository checkout | Yes | **Yes** — supported submission model |

See [`installation-model.md`](installation-model.md) and `python3 mcp/govai_mcp_server.py installation-check`.

## Committed listing artefacts

| Asset | Path | Status |
| --- | --- | --- |
| Manifest logo | `assets/logo.png` | committed |
| Marketplace hero | `assets/listing/govai-marketplace-hero-2400x800.png` | committed |
| Screenshot 1 — installation check | `assets/listing/govai-cursor-mcp-01-installation-check.png` | committed |
| Screenshot 2 — gate pass | `assets/listing/govai-cursor-mcp-02-gate-pass.png` | committed |
| Screenshot 3 — evidence validation | `assets/listing/govai-cursor-mcp-03-evidence.png` | committed |
| Screenshot 4 — audit dry-run | `assets/listing/govai-cursor-mcp-04-dry-run.png` | committed |
| Screenshot 5 — rules panel | `assets/listing/govai-cursor-mcp-05-rules.png` | committed |
| Demo-flow evidence | `assets/capture-evidence/demo-flow-evidence.json` | committed |

`make cursor-marketplace-listing-check` passes when all committed assets remain on disk and `brand-derivation.json` matches `aigov-mark.ico`.

## Still external / pending

- Legal/marketing sign-off
- Cursor publisher submit and vendor approval
- Approved listing URL from Cursor (record only after approval)

## Next maintainer actions

1. After editing `dashboard/brand/aigov-mark.ico`, run `./scripts/sync_cursor_marketplace_brand_from_ico.sh`.
2. Re-capture listing screenshots if product UI changes materially.
3. Run `make cursor-marketplace-listing-check` before portal upload.
4. Submit via Cursor portal using [`submission-copy.md`](submission-copy.md).
5. Update this file **only** when Cursor provides an approved listing URL.
