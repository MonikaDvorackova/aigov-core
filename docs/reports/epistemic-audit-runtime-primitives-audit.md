# Epistemic audit runtime primitives audit

## Summary

Extends AIGov Core epistemic readiness from compliance-oriented replay checks toward **epistemic traceability**: explicit classification of what is known, evidenced, inferred, changed, and unverifiable for audit exports.

## Thesis alignment

Knowledge Preservation Architecture treats governance exports as Decision Knowledge carriers. These primitives make reconstructability gaps legible to auditors without introducing a second authoritative store.

## Changes

| Area | Change |
|------|--------|
| `rust/src/epistemic_readiness.rs` | Extended `DecisionKnowledge` trace slices; `EpistemicGapReport`; `KnowledgeContinuityValidation`; drift requirements |
| `rust/src/trace_verification_plan.rs` | **New** — build `TraceVerificationPlan` from export readiness requirements |
| `rust/src/audit_export.rs` | Attach `trace_verification_plan` on export build |
| `rust/src/lib.rs` | Export `trace_verification_plan` module |
| `python/aigov_py/epistemic_readiness.py` | Summary output for trace slices and structured gaps |
| `docs/epistemic-audit-primitives.md` | **New** — primitive reference |
| `examples/epistemic-readiness/README.md` | **New** — scenario catalog |

## Preserved APIs

- Ledger and `aigov.audit_export.v1` evidence remain authoritative
- `govai epistemic-readiness` command unchanged (extended JSON fields)
- Schema `aigov.epistemic_readiness.v1` retained with additive fields

## Validation

```bash
cd rust && cargo test --all --locked
cd .. && python -m pytest
make gate
make cursor-plugin-smoke
```

Focused:

```bash
cd rust && cargo test --locked epistemic
govai epistemic-readiness --export audit_export.json --json
```

## Risk assessment

Low–medium.

Additive derived fields on export and readiness JSON. No verdict semantics or ledger mutation. Consumers ignoring new fields remain compatible.

## Evaluation gate

- [x] DecisionKnowledge trace slices populated from export + replay
- [x] KnowledgeContinuity validation helper
- [x] EpistemicGapReport with remediation hints
- [x] TraceVerificationPlan attached to exports
- [x] Deterministic tests for required scenarios
- [x] CLI verification path documented

## Human approval gate

Review before merge to staging. Confirm gap taxonomy matches `docs/architecture/epistemic-model.md`.
