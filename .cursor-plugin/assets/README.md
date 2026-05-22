# GovAI Cursor plugin — marketplace and distribution assets

This directory holds **documentation and naming guidance** for visual and demo assets used when publishing the GovAI Cursor plugin (Marketplace, product pages, and partner decks). **`logo.png`** is committed here as the **plugin manifest logo** (copied from `dashboard/public/icon-512.png` for Marketplace `logo` field compliance). Other large binaries (heroes, screenshots, video) remain **optional** per your release policy.

## Required logo sizes

| Asset | Dimensions | Notes |
|-------|------------|--------|
| App icon (square) | 512×512 px minimum | PNG with transparent background where the platform allows; provide 1024×1024 px for downscaling quality if required. |
| Small toolbar / list icon | 128×128 px and 256×256 px | Derived from the master square; keep critical detail inside the central 80% safe area. |
| Monochrome variant | Same aspect as colour master | For dark-on-light and light-on-dark UI themes; test contrast on grey backgrounds. |

## Banner dimensions

| Surface | Suggested size | Notes |
|---------|----------------|--------|
| Marketplace hero / header | 2400×800 px (3:1) | Safe text and logo within a central 1600×640 px region; expect aggressive cropping on narrow viewports. |
| Social / link preview | 1200×630 px | Open Graph style; keep primary message in the centre third. |
| Repository social image | 1280×640 px | GitHub-style; avoid fine print below 12 px effective size. |

## Screenshot recommendations

Capture **real Cursor UI** with GovAI rules, skills, or MCP tools visible:

- **MCP connected**: Settings or `mcp.json` showing `govai-local` (or your server name) with stdio command and repo-relative path to `mcp/govai_mcp_server.py`.
- **Gate success**: Terminal or MCP tool output after `govai-gate-reports` or `make gate` with a clear PASS summary.
- **Evidence validation**: Output from evidence-pack verification against `examples/standards/` or a customer-safe redacted pack.
- **Audit report flow**: `docs/reports/` with a report open that shows evaluation and human approval headings (redact customer data).

Use **consistent window chrome**, **light and dark** variants where possible, and **PNG** for UI (avoid JPEG artefacts on text).

## Demo video recommendations

| Topic | Duration | Content |
|-------|----------|---------|
| First install | 60–90 s | Install plugin, wire MCP from `examples/local-config.json`, restart Cursor. |
| First compliance check | 90–120 s | Run read-only MCP tools or Makefile targets; show gate PASS. |
| Enterprise story | 3–5 min | SSO, hosted vs OSS, audit retention (high level; no customer secrets). |

Technical guidance:

- **1080p minimum**, 16:9, captioned (SRT or burned-in captions for accessibility).
- Show **keyboard shortcuts** sparingly; prefer visible clicks for reproducibility.
- End with a **single call to action** (documentation URL or contact).

## Branding guidelines

- **Name**: Use **GovAI** consistently in titles; spell out “AI governance” in body copy where clarity helps.
- **Tone**: Precise, operator-first, no implied legal certification unless counsel approves specific wording.
- **Claims**: Align screenshots and copy with what the OSS repo and hosted product **actually** ship; distinguish **local IDE assistant** from **hosted audit service** and **Rust enforcement**.
- **Colours**: Derive palette from your design system; document primary, secondary, and accessible text pairs (WCAG AA minimum for body text on backgrounds).

## File naming conventions

Use **lowercase**, **hyphens**, and **version or date suffixes** where teams ship multiple crops:

| Pattern | Example |
|---------|---------|
| Square logo master | `govai-logo-master-1024.png` |
| Marketplace hero | `govai-marketplace-hero-2400x800.png` |
| Screenshot sequence | `govai-cursor-mcp-01-connected.png`, `govai-cursor-mcp-02-gate-pass.png` |
| Demo video | `govai-cursor-plugin-quickstart-1080p-en.mp4` |

Store large binaries **outside** git if your policy requires (object storage or release attachments) and keep this README as the **canonical checklist** for what to produce before submission.
