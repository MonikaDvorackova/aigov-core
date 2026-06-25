# Epistemic readiness scenario catalog

Deterministic fixtures for epistemic audit runtime primitives. Scenarios are implemented as unit tests in `rust/src/epistemic_readiness.rs` and produce stable gap codes.

| Scenario | Expected signals | Test |
|----------|------------------|------|
| `valid_run` | `status=ready`, empty gaps | `valid_run_full_reconstructability` |
| `missing_evidence` | `missing_evidence_reference` gap | `missing_evidence_reference_signal` |
| `model_drift` | `model_artifact_drift` gap, `changed.model_artifact_drift` claim | `model_artifact_drift_detected` |
| `policy_drift` | `policy_version_drift` gap | `policy_version_drift_detected` |
| `unverifiable_output` | `unverifiable.external_artifact`, `unverifiable.policy_artifact` | `unverifiable_external_artifact_paths` |
| `replay_mismatch` | `changed.replay_verdict_mismatch`, invalid compliance | `replay_verdict_mismatch_surfaces_in_changed` |
| `replay_tamper` | digest / replay validation failure | `replay_validation_failure_tampered_digest` |

## Regenerating exports

Golden-path exports with epistemic blocks are produced by the runtime export builder:

```bash
cd rust && cargo test --locked export_full_event_chain_and_schema_shape
```

Offline evaluation:

```bash
govai epistemic-readiness --export path/to/audit_export.json --json
```
