# Deterministic governance replay

GovAI Core can **reconstruct governance state** from an exported `aigov.audit_export.v1` document without contacting a live runtime. Replay recomputes evaluation, approval, and promotion projection and derives the same **VALID / INVALID / BLOCKED** verdict rules used by `GET /compliance-summary`.

This is **not** distributed tracing or log replay. It is **ledger-authoritative governance reconstruction** from append-only evidence.

## Replay semantics

Given `evidence_events` and `evidence_hashes` from an export:

1. **Validate** schema, `run_id` consistency, duplicate `event_id`s, stable event ordering, hash-chain continuity, and `events_content_sha256`
2. **Project** governance state using the same Rust projection as the audit service
3. **Derive** compliance verdict from projected state
4. **Compare** replayed verdict to `decision.verdict` in the export

Replay **succeeds** when validation passes and the reconstructed verdict matches the export.

## Reconstructibility

A run is reconstructible when:

- Evidence is **append-only** and hash-linked (`log_chain`)
- Event ordering in the export matches deterministic stable order
- Content digests in the export match recomputation from events
- Verdict in the export matches projection from those events

The [reconstructible agent demo](../examples/reconstructible-agent-demo/) shows the full lifecycle; this document covers the **offline engine** that verifies exports.

## Deterministic governance projection

Projection walks evidence in stable order (`ts_utc`, `event_type`, `event_id`) and rebuilds:

- Discovery signals and evidence requirements
- Evaluation state (`evaluation_reported` / `evaluation_passed`)
- Risk and human approval state
- Promotion state

The replay engine uses `replay_projection.rs` (wraps `projection.rs` + `compliance_summary.rs`). Two replays of the same export JSON produce the same `determinism_digest`.

## Replay vs tracing

| Tracing / observability | GovAI deterministic replay |
|-------------------------|------------------------------|
| Sampled spans, best-effort order | Ordered evidence events |
| Inferred outcomes | Ledger projection rules |
| No compliance verdict contract | VALID / INVALID / BLOCKED |
| Debugging latency | Audit and regulatory reconstruction |

## Why event ordering matters

Compliance projection uses **last matching event** semantics for several fields. Reordering events with the same timestamp can change approval or promotion interpretation. The engine flags **reordered_events** when `evidence_events` diverges from stable order or from `log_chain` order.

## Why append-only guarantees matter

Append-only ledgers provide:

- **Duplicate rejection** at ingest (`event_id` uniqueness)
- **Hash chain** linkage (`prev_hash` → `record_hash`)
- **Deterministic export digests** for offline verification

Replay validation detects broken chains, duplicate IDs, and digest tampering without mutating the ledger.

## CLI

Build the replay helper:

```bash
cd rust && cargo build --bin replay_audit_export_once
```

Run via GovAI CLI:

```bash
govai replay-audit-export --path exports/run-123.json
govai replay-audit-export --path exports/run-123.json --json
```

Environment override:

```bash
export GOVAI_REPLAY_AUDIT_EXPORT_BIN=/path/to/replay_audit_export_once
```

## Output

Human-readable mode explains:

- Why a verdict is **BLOCKED** (missing evidence, awaiting approval, promotion state)
- What unlocked **VALID** (evaluation passed, human approval, promotion)
- Which gates contributed (evaluation, human approval, evidence requirements)
- Lifecycle transitions in evidence order

JSON mode returns the full `ReplayResult` structure including `validation`, `integrity`, and `projection.explanation`.

## Implementation

| Module | Role |
|--------|------|
| `rust/src/replay_validation.rs` | Schema, ordering, chain, digests, lifecycle checks |
| `rust/src/replay_projection.rs` | State projection and explanations |
| `rust/src/replay_engine.rs` | Orchestration and `ReplayResult` |
| `python/aigov_py/replay_audit_export.py` | CLI wrapper |

Tests: `rust/src/replay_engine.rs` unit tests, `cargo test --locked`.

## Related

- [Runtime API contract](runtime-api-contract.md)
- [Reconstructible agent demo](reconstructible-agent-demo.md)
- [Signed evidence bundles](signed-evidence-bundles.md)
- [Governance semantics](architecture/governance-semantics.md)
