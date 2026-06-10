# Cursor plugin — release checklist

**Publication status:** pre-submit maintainer steps. Documentation-ready in-repo ≠ live listing.

Checked items below are validated against [`checklist-state.json`](checklist-state.json).

## Before tagging or submitting

- [x] <!-- id:status-not-live --> Read [`status.md`](status.md) — confirms **not live** / **not approved** / **`aigov-mark.ico`** approved source.
- [x] <!-- id:cursor-plugin-check --> Demo-flow evidence JSON passes (`scripts/record_cursor_marketplace_demo_evidence.py`).
- [x] <!-- id:plugin-json-metadata --> `plugin.json` fields match portal limits.
- [x] <!-- id:submission-copy-synced --> [`submission-copy.md`](submission-copy.md) synced with `plugin.json` and [`../marketplace.md`](../marketplace.md).
- [x] <!-- id:cursor-version-policy --> [`cursor-version-policy.md`](cursor-version-policy.md) documents tested Cursor baseline.
- [x] <!-- id:installation-model-documented --> [`installation-model.md`](installation-model.md) documents full-repository MCP requirement.
- [x] <!-- id:logo-committed --> Manifest logo committed at `assets/logo.png` (from `dashboard/brand/aigov-mark.ico`).
- [x] <!-- id:marketplace-hero --> Marketplace hero committed at `assets/listing/govai-marketplace-hero-2400x800.png`.
- [x] <!-- id:real-screenshots --> Real Cursor UI screenshots committed per manual procedure.
- [x] <!-- id:manual-capture-procedure --> [`manual-capture-procedure.md`](manual-capture-procedure.md) documents screenshot capture.
- [x] <!-- id:marketplace-assets-manifest --> `assets/marketplace-assets.json` status fields accurate.
- [x] <!-- id:rules-skills-no-scaffold-tokens --> Rules/skills pass scaffold-token validator.
- [x] <!-- id:reviewer-notes --> [`reviewer-notes.md`](reviewer-notes.md) ready for reviewers.
- [x] <!-- id:support-contact --> [`support-and-contact.md`](support-and-contact.md) ready for listing.
- [ ] <!-- id:legal-marketing-review --> Legal/marketing review complete.

## Submission portal (external)

- [ ] <!-- id:portal-submit --> Upload logo, hero, and screenshots; paste `submission-copy.md`; attach reviewer notes.
- [ ] <!-- id:cursor-approval --> Cursor approval and live listing URL recorded (then update `status.md` only).

## After Cursor approval (future)

- Update [`status.md`](status.md) with live listing URL when it exists.
- Pin release note with limitations from `submission-copy.md`.
