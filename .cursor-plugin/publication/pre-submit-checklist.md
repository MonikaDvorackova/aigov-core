# Pre-submit checklist — go / no-go

**Publication status:** repository pre-submit review. **Not live** in Cursor Marketplace until Cursor approves a listing and a maintainer updates `status.md` with the approved listing URL.

Evidence IDs map to [`checklist-state.json`](checklist-state.json) and [`checklist-evidence.json`](checklist-evidence.json). CI validates checked items against evidence.

## Repository GO — documentation and plugin validation

- [x] <!-- id:status-not-live --> `status.md` states **not live**, **not approved**, and approved source **`aigov-mark.ico`**.
- [x] <!-- id:cursor-plugin-check --> `demo-flow-evidence.json` records passing MCP CLI demo (`make cursor-plugin-check` equivalent).
- [x] <!-- id:plugin-json-metadata --> `plugin.json` metadata complete.
- [x] <!-- id:submission-copy-synced --> `submission-copy.md` synced; no false live claims.
- [x] <!-- id:cursor-version-policy --> Supported Cursor version policy documented.
- [x] <!-- id:installation-model-documented --> Full-repository MCP requirement documented (`installation-model.md` + `installation-check` CLI).
- [x] <!-- id:logo-committed --> Manifest logo committed at `assets/logo.png` (derived from `dashboard/brand/aigov-mark.ico`).
- [x] <!-- id:marketplace-hero --> Marketplace hero committed at `assets/listing/govai-marketplace-hero-2400x800.png`.
- [x] <!-- id:real-screenshots --> Five listing screenshots committed under `assets/listing/govai-cursor-mcp-0*.png`.
- [x] <!-- id:demo-flow-evidence --> Demo-flow CLI evidence JSON committed.
- [x] <!-- id:reviewer-notes --> Reviewer notes present.
- [x] <!-- id:support-contact --> Support and contact documented.
- [x] <!-- id:manual-capture-procedure --> Manual screenshot procedure documented.
- [x] <!-- id:marketplace-assets-manifest --> `marketplace-assets.json` tracks committed assets with `aigov-mark.ico` source.

## Repository NO-GO — block portal submit until resolved

- [ ] <!-- id:legal-marketing-review --> Legal/marketing sign-off that copy does not imply regulatory certification.
- [ ] <!-- id:portal-submit --> Maintainer submitted package in Cursor publisher portal.
- [ ] <!-- id:cursor-approval --> Cursor approval received and approved listing URL recorded (external).

## Go / no-go decision

| Decision | When |
| --- | --- |
| **GO (repository docs)** | All items in **Repository GO** are checked and evidence-validated. |
| **GO (portal upload)** | Repository GO plus `legal-marketing-review` and `make cursor-marketplace-listing-check` pass. |
| **GO (public listing live)** | Cursor provides approval and listing URL; then update `status.md` — never before. |

Current recommendation: **GO (repository docs)** and **GO (portal upload)** pending legal/marketing sign-off only.
