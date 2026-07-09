# Staging to main release audit

## Summary

This report documents the staging to main promotion for the current aigov-core release batch.

The release includes Cursor Marketplace plugin packaging, publisher logo assets, runtime observability diagnostics, frontend and documentation updates, CI readiness fixes, and schema alignment fixes for runtime diagnostics evidence events.

## Evaluation gate

The staging branch was validated as the integration branch before promotion to main.

Validation scope includes:

- Cursor Marketplace plugin package and publication readiness assets.
- Runtime observability diagnostics.
- Rust evidence event schema alignment for runtime diagnostics.
- Frontend and documentation updates included in the staging release.
- Repository CI for the staging to main pull request.

The runtime diagnostics ledger probe was aligned with the current EvidenceEvent schema by including the optional delegation and trace context fields.

The Cursor plugin package remains a submission package and is not marked as live in Cursor Marketplace.

## Human approval gate

This staging release is approved for main promotion once the staging to main pull request CI passes.

External publication steps remain separate and are not completed by this repository merge:

- Cursor publisher registration.
- Cursor Marketplace submission.
- Cursor vendor approval.
