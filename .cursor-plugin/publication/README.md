# Cursor Marketplace — publication package

Single maintainer entry point for the AIGov Cursor plugin **first submission**. This package is **documentation-ready** in the repository; listing media is **incomplete**; it is **not** a claim of Cursor Marketplace approval or a live listing.

**Authoritative status:** [`status.md`](status.md)

## Files

| File | Purpose |
| --- | --- |
| [status.md](status.md) | Internally usable / listing media incomplete / not live |
| [submission-copy.md](submission-copy.md) | Short and long listing copy, categories, limitations |
| [demo-flow.md](demo-flow.md) | Reviewer and maintainer demo script |
| [screenshot-plan.md](screenshot-plan.md) | Ordered still captures and alt-text guidance |
| [reviewer-notes.md](reviewer-notes.md) | Security model, tool surface, review order |
| [support-and-contact.md](support-and-contact.md) | Issues, email, SLA framing |
| [cursor-version-policy.md](cursor-version-policy.md) | Tested Cursor versions and upgrade policy |
| [release-checklist.md](release-checklist.md) | Pre-submit maintainer steps (evidence-backed checkboxes) |
| [pre-submit-checklist.md](pre-submit-checklist.md) | Go / no-go criteria for portal open vs upload vs live listing |
| [installation-model.md](installation-model.md) | Full-repository MCP requirement audit |
| [manual-capture-procedure.md](manual-capture-procedure.md) | Deterministic real screenshot capture steps |
| [checklist-state.json](checklist-state.json) | Completed vs pending item IDs |
| [checklist-evidence.json](checklist-evidence.json) | Evidence registry for completed items |

## Assets

| Resource | Location |
| --- | --- |
| Asset manifest (machine-readable) | [`../assets/marketplace-assets.json`](../assets/marketplace-assets.json) |
| Manifest logo (from `aigov-mark.ico`) | [`../assets/logo.png`](../assets/logo.png) |
| Demo-flow CLI evidence | [`../assets/capture-evidence/demo-flow-evidence.json`](../assets/capture-evidence/demo-flow-evidence.json) |
| Missing hero/screenshots | [`../assets/listing/README.md`](../assets/listing/README.md) |

## Validation

From the repository root:

```bash
make cursor-plugin-check
```

Runs `scripts/validate_cursor_plugin.py` (manifest, publication structure, brand derivation) and `scripts/smoke_cursor_plugin.py`.

Strict listing-media gate (all committed assets on disk; ICO derivation hashes must match):

```bash
make cursor-marketplace-listing-check
```

## Internal vs Marketplace scope

| Layer | Ready when |
| --- | --- |
| Clone-and-use | `make cursor-plugin-check` passes; full repo workspace |
| Documentation package | This folder + `marketplace-assets.json` + missing-media docs |
| Portal upload | `make cursor-marketplace-listing-check` passes + legal review |
| Live listing | Maintainer submit + Cursor approval — **not done yet** |
