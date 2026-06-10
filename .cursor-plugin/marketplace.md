# AIGov Cursor plugin — Marketplace submission draft

**Publication status:** [`publication/status.md`](publication/status.md) — internally usable, submission-ready, **not live** in Cursor Marketplace.

Canonical listing copy for portal paste lives in [`publication/submission-copy.md`](publication/submission-copy.md). This file is a maintainer index; keep both in sync on release.

## Product name

AIGov

## Tagline

Deterministic governance gates and audit-ready evidence workflows inside Cursor.

## Short description

See [`publication/submission-copy.md`](publication/submission-copy.md#short-description-400-characters).

## Long description

See [`publication/submission-copy.md`](publication/submission-copy.md#long-description).

## Categories

- Developer productivity
- Security / compliance tooling

## Target users

- Platform and compliance engineers maintaining AI governance pipelines.
- Developers on AIGov-integrated repositories who want IDE-native gate checks.
- Teams preparing EU AI Act–aligned documentation and evidence packs (non-legal workflow support).

## Key capabilities

- Cursor **rules** for branch policy, audit-report requirements, and compliance gates.
- **Skills** for triaging gate failures, creating evidence packs, preparing audit reports, and mapping controls.
- **MCP tools**: pytest runner, evidence validation, report heading gate, `make gate`, audit template generation with **dry-run**.
- **Validation**: `make cursor-plugin-check` (manifest, publication package, MCP smoke).

## Demo workflow

Follow [`publication/demo-flow.md`](publication/demo-flow.md).

## Required screenshots

Follow [`publication/screenshot-plan.md`](publication/screenshot-plan.md). Asset manifest: [`assets/marketplace-assets.json`](assets/marketplace-assets.json).

## Support and versions

- [`publication/support-and-contact.md`](publication/support-and-contact.md)
- [`publication/cursor-version-policy.md`](publication/cursor-version-policy.md)
- [`publication/reviewer-notes.md`](publication/reviewer-notes.md)

## Limitations

- **Not** a certified compliance product; organisational policies and hosted services remain authoritative.
- MCP server is a **minimal** stdio implementation, not a full-featured remote MCP deployment.
- **Linux/macOS-oriented** examples; Windows paths may need adjustment in local MCP config.
- Full `make gate` can be slower than `gate_reports` alone; timeouts may need tuning on very large monorepos.

## Submission checklist

See [`publication/release-checklist.md`](publication/release-checklist.md) and [`../docs/commercial/marketplace-submission-checklist.md`](../docs/commercial/marketplace-submission-checklist.md).
