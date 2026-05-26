# Multi Agent Lineage Governance Graph

## Summary

Adds multi-agent lineage fields on evidence events, governance graph projection (`governance_graph`, `lineage_projection`, `lineage_validation`), backward-compatible `lineage` metadata on `aigov.audit_export.v1`, replay-integrated lineage checks, `govai lineage-graph` / `lineage_graph_once` with optional Mermaid output, documentation, threat-model extension, and `make lineage-governance-check` in CI.

## Evaluation gate

**Delegated evaluation evidence remains ledger-authoritative and replay-deterministic.** `evaluation_reported` on each run scope is projected with the same policy rules during `govai replay-audit-export`. Lineage graph edges do not override evaluation outcomes; missing evaluation on a delegated run still yields **INVALID** via standard projection.

## Human approval gate

**Approvals remain append-only lineage evidence across delegated runs.** `human_approved` events are immutable ledger records linked in the governance graph as governance gates. Delegation does not imply approval; subgraphs without `human_approved` remain **BLOCKED** when policy requires it.

## Lineage reconstruction

Operators reconstruct flows by:

1. Exporting each `run_id` (or reviewing combined export `lineage` block)
2. Running `govai lineage-graph --path export.json` for integrity, orphans, and delegation chains
3. Running `govai replay-audit-export` for verdict and lifecycle validation
4. Optionally correlating `root_run_id` / `parent_run_id` across multiple exports

Deterministic ordering uses `(ts_utc, event_id)` for stable replay and Mermaid output.

## Verification

```bash
make lineage-governance-check
make runtime-packaging-check
make reconstructible-demo-check
make reference-integrations-check
make core-runtime-examples-check
make gate
cd rust && cargo build --locked --bin aigov_audit && cargo test --locked
cd ..
```

Optional:

```bash
cd rust && cargo build --bin lineage_graph_once
govai lineage-graph --path /path/to/export.json
govai lineage-graph --path /path/to/export.json --mermaid
```
