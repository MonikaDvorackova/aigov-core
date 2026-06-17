# Epistemic readiness

Epistemic readiness measures whether a governance run’s **audit export** carries enough **Decision Knowledge** to reconstruct promotion eligibility years later — without treating compliance validity as sufficient.

It is **derived** at export or offline evaluation time. It is **not** stored in the ledger and is **not** authoritative for verdicts.

See also: [architecture/epistemic-model.md](architecture/epistemic-model.md).

## What it answers

| Question | Field |
|----------|--------|
| Did export-time compliance claim `VALID` and replay agree? | `compliance_verdict_valid` |
| Can governance be replayed from the export alone? | `reconstructable` |
| Is policy still retrievable for rule set `R`? | `continuity.policy_artifact_retrievable` |
| Is delegation lineage intact? | `continuity.lineage_resolved` |
| Overall epistemic posture | `status`: `ready` \| `partial` \| `not_ready` |

A run may be **compliance-valid** (`VALID` + replay match) but **epistemically partial** — for example when `policy_version` is present but the policy file is no longer archived.

`confidence` is always `non_authoritative: true`. It is advisory only.

## CLI

```bash
# Human summary
govai epistemic-readiness --export path/to/audit_export.json

# Structured JSON (schema aigov.epistemic_readiness.v1)
govai epistemic-readiness --export path/to/audit_export.json --json
```

Build the Rust helper if needed:

```bash
cd rust && cargo build --bin epistemic_readiness_once
export GOVAI_EPISTEMIC_READINESS_BIN=$PWD/target/debug/epistemic_readiness_once
```

Optional: mark policy artifact as available for offline evaluation:

```bash
export GOVAI_POLICY_ARTIFACT_AVAILABLE=true
```

When unset, offline evaluation conservatively assumes the policy artifact is **not** retrievable.

## Export integration

`build_audit_export_v1` attaches an `epistemic_readiness` block computed at export time with `policy_artifact_available: true` (policy was loaded to build the export). Re-evaluating the same file later without policy archives may yield `partial`.

## Gap codes

Readiness gaps (sorted, deterministic) include:

- `unsupported_schema_version`
- `replay_validation_failure`
- `missing_policy_reference`
- `missing_policy_artifact`
- `missing_evidence_reference` (from bundle verification signals)
- `unresolved_lineage`
- `unsigned_dependency`
- `events_digest_continuous` / `chain_continuous` (continuity failures)

## Non-goals

- No mutable knowledge graph
- No model understanding or prompt retention
- No second source of truth — ledger and export evidence remain canonical
