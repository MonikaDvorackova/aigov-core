# Microbenchmarks (synthetic audit-chain operations)

GovAI ships a **stdlib-only** microbenchmark driver that measures **synthetic** hash-chain construction, verification, a toy compliance projection, and JSON export serialization. This complements production-oriented observability under `docs/observability/` but does **not** replace load testing of the Rust HTTP service.

## What is measured

| Benchmark | Meaning |
|-----------|---------|
| `event_creation_throughput_events_per_sec` | SHA256-linked synthetic appends per second (warmup applied) |
| `hash_chain_verification_seconds` | Full linear verification of a synthetic chain |
| `compliance_derivation_seconds` | Deterministic toy check over parsed events |
| `export_generation_seconds` | JSON serialization of all records |

## Determinism

- **Structural determinism:** fixed JSON key ordering, fixed RNG seeds, fixed `version` field in machine output.
- **Timing values** vary by CPU; CI should assert `ok` and schema presence, not nanosecond stability.

## How to run

```bash
python3 scripts/microbenchmark_audit_engine.py --json
```

```bash
bash examples/research/run-microbenchmarks.sh
```

Makefile target: `make microbenchmark-check`

## Relationship to the hosted engine

The synthetic hash rule mirrors the ledger record hash construction documented in `rust/src/audit_store.rs` (`prev_hash`, newline, `event_json`). The **authoritative** compliance verdict remains `GET /compliance-summary` on a deployed service; microbenchmarks do not exercise Postgres, tenancy, or billing.

## Related

- `docs/research/quantitative-feasibility.md`
- `docs/research/benchmark-methodology.md`
