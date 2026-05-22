# Empirical evaluation (GovAI reference implementation)

This document describes **empirically measured** performance characteristics of the audit-engine **hot paths** as exercised by the repository benchmark harness. Measurements are **real wall-clock timings** on the machine executing the harness (CPU, memory bandwidth, interpreter overhead).

## What is measured

| Category | Artefact | Notes |
|----------|----------|------|
| Event ingestion pipeline | `scripts/run_event_ingestion_benchmarks.py` | JSON construction plus SHA-256 record hashing per event |
| Hash-chain verification | `scripts/run_hash_chain_benchmarks.py` | Full linear verification over in-memory chains |
| Export / compression | `scripts/run_export_benchmarks.py` | `json.dumps` plus `gzip.compress` |
| Storage projections | `scripts/run_storage_benchmarks.py` | Derived from measured average bytes per event |
| Multi-tenant synthetic load | `scripts/run_multi_tenant_benchmarks.py` | Sequential tenant-scoped workloads |
| Failure detection | `scripts/run_failure_benchmarks.py` | Time to detect invalid chain or classify stub policy states |

## What is not measured

- End-to-end HTTP load against a production cluster at datacenter scale (unless you opt into optional HTTP probes).
- Database query planning under concurrent writers across many nodes.
- Statistical inference over a population of independent deployments.

## Machine-readable outputs

Results are written to `benchmark-runs/latest/` (gitignored) with deterministic JSON key ordering. The orchestrator is `scripts/run_full_empirical_evaluation.py`; validation is `scripts/empirical_evaluation_check.py`.

## Quick mode

Set `GOVAI_EMPIRICAL_QUICK=1` to reduce workload size (ingestion uses **1 KiB and 4 KiB** payloads with **1 000 and 10 000** events per scenario; hash-chain verification to **10 000** events; multi-tenant to **100** tenants with fewer ops per tenant) while preserving the same measurement methodology. CI enables this by default.

## Related

- `docs/research/load-testing-methodology.md`
- `docs/research/statistical-methodology.md`
- `docs/research/benchmark-manifest.json`
