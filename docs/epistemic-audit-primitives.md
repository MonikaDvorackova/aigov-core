# Epistemic audit runtime primitives

GovAI Core exposes **derived** epistemic traceability primitives on top of `aigov.audit_export.v1`. They answer what is **known**, **evidenced**, **inferred**, **changed**, and **unverifiable** for a governance run — without replacing ledger authority or compliance verdicts.

This aligns with Knowledge Preservation Architecture: audit logging records events; epistemic primitives classify reconstructability and continuity gaps for years-later review.

## Primitives

| Primitive | Schema / type | Role |
|-----------|---------------|------|
| `DecisionKnowledge` | nested in `aigov.epistemic_readiness.v1` | Run-scoped knowledge carrier with trace slices (`known`, `evidenced`, `inferred`, `changed`, `unverifiable`) |
| `KnowledgeContinuity` | same | Boolean continuity flags (chain, digest, policy, lineage) |
| `KnowledgeContinuityValidation` | same | Actionable failure list from continuity flags |
| `EpistemicGapReport` | `aigov.epistemic_gap_report.v1` | Structured gaps with severity and remediation |
| `TraceVerificationPlan` | `govai.standards.trace_verification_plan.v1` | Deterministic verification plan for external audit review |

## CLI verification

```bash
# Human summary (includes trace slices and structured gaps when present)
govai epistemic-readiness --export path/to/audit_export.json

# Full derived document (schema aigov.epistemic_readiness.v1)
govai epistemic-readiness --export path/to/audit_export.json --json
```

Build the Rust evaluator:

```bash
cd rust && cargo build --bin epistemic_readiness_once
export GOVAI_EPISTEMIC_READINESS_BIN=$PWD/target/debug/epistemic_readiness_once
```

Optional offline policy artifact signal:

```bash
export GOVAI_POLICY_ARTIFACT_AVAILABLE=true
```

## Export integration

`build_audit_export_v1` attaches:

- `epistemic_readiness` — derived readiness snapshot
- `trace_verification_plan` — derived verification plan with `plan_digest`

Both are **recomputable** and non-authoritative.

## Deterministic scenario fixtures

See [examples/epistemic-readiness/README.md](../examples/epistemic-readiness/README.md) for catalogued scenarios exercised in `rust/src/epistemic_readiness.rs` tests:

- missing evidence reference (bundle signal)
- model artifact drift (`model_trained` vs `model_promoted` digest mismatch)
- policy version drift (carrier field mismatch)
- unverifiable external artifact paths and policy bytes
- replay verdict mismatch

## Related docs

- [epistemic-readiness.md](epistemic-readiness.md)
- [architecture/epistemic-model.md](architecture/epistemic-model.md)
- [standards/trace_verification_plan_schema.md](standards/trace_verification_plan_schema.md)
