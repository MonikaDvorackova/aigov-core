# Quantitative feasibility and analytical cost model

This document provides an **illustrative analytical cost model** and parameter ranges for planning GovAI-style audit-backed governance. It is **not** a formal economic study, peer-reviewed cost estimate, or statistically inferred demand forecast.

## Scope

- **In scope:** Order-of-magnitude storage and latency relationships, deployment archetypes, explicit assumptions.
- **Out of scope:** Vendor-specific list prices, court-weighted damages, or population-level willingness-to-pay inference.

## Storage cost model

Let:

- **B** = average bytes per evidence event JSON (payload + metadata), after UTF-8 encoding.
- **E** = events per `run_id` (lifecycle: build, evaluate, approve, promote, export hooks).
- **R** = runs per month (CI jobs, releases, experiments).

Illustrative parameter ranges (operator-measured values supersede these defaults):

| Symbol | Conservative | Typical | Stress |
|--------|--------------|---------|--------|
| B | 1.5 KiB | 4 KiB | 12 KiB |
| E | 40 | 200 | 800 |
| R | 500 | 5 000 | 50 000 |

**Monthly append-only ledger growth (single tenant, uncompressed JSONL)** is approximately `B × E × R`.

Example (typical column): 4 KiB × 200 × 5 000 ≈ **4 GiB/month** of primary ledger text before replication and indices.

Checkpoints, workflow tables, and Postgres indexes add **multiplicative overhead** (often 1.5×–4×) depending on retention and vacuum settings.

## Latency model

Components (order-of-magnitude; self-hosted vs hosted differs):

| Stage | Dominant factors | Notes |
|-------|------------------|------|
| Event ingestion (`POST /evidence`) | Policy evaluation, disk append, fsync policy | Fail-closed rules increase CPU, not necessarily I/O |
| Hash-chain verification | Linear scan of JSONL | See `GET /verify-log` and `rust/src/audit_store.rs` |
| Bundle / export | Read + serialize projection | `GET /bundle`, `GET /api/export/:run_id` |

Microbenchmarks that exercise **synthetic** hash chains without the full HTTP stack live in `docs/research/microbenchmarks.md` and `scripts/microbenchmark_audit_engine.py`.

## Operational cost scenarios

### Small deployment

Single team, self-hosted Postgres, local or single-region object storage, manual approvals. Cost drivers: operator time, modest VM storage, backup window.

### Enterprise deployment

Multi-tenant isolation, RBAC, SSO, regional residency, higher R and E. Cost drivers: replicated storage, observability stack, support SLAs, security review cycles.

### Regulator-facing deployment

Long retention, legal hold workflows, read-only analyst roles, frequent exports. Cost drivers: **immutable** or WORM-compatible storage, search/index for investigations, egress controls.

## Disclaimer

Figures here are **planning aids**. Production totals require measured **B**, **E**, and **R** from your telemetry plus cloud/storage pricing. GovAI **does not** certify financial outcomes or regulatory budgets.

## Related artefacts

- `docs/research/microbenchmarks.md`
- `scripts/microbenchmark_audit_engine.py`
- `docs/trust-model.md` (what VALID does and does not imply)
