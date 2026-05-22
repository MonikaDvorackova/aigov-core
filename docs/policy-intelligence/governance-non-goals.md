# Governance non-goals

Policy intelligence and the governance control plane **do not**:

- Change **runtime enforcement** semantics, audit API behavior, or verdict computation.
- Run **database migrations** or mutate **ledger** state.
- Perform **billing**, metering, or subscription changes.
- Replace **legal or regulatory** advice; scores and reports are planning aids only.

They **do**:

- Validate manifests and snapshot schemas.
- Emit deterministic JSON and Markdown for CI and documentation gates.
- Encourage consistent documentation of coverage, maturity, gaps, and review cadence.

## Related

- [`README.md`](README.md) in this directory for the manifest and tooling index.
