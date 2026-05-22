# Runtime safety, guardrails, and human oversight

Phase 21 provides **offline**, **deterministic** tooling to reason about GovAI-related runtime safety: input and tool guardrails, escalation to humans, oversight coverage, and emergency override readiness. It complements [runtime observability](../observability/README.md) by focusing on **safety posture** rather than generic service health.

## Machine-readable index

- [`runtime-safety-manifest.json`](runtime-safety-manifest.json) — weights, signal catalogue, probes, and references.

## Validators and scoring

From the repository root:

```bash
python3 scripts/validate_runtime_safety_manifest.py --json
python3 scripts/validate_runtime_safety_snapshot.py --input examples/runtime-safety/sample-runtime-safety-snapshot.json --json
python3 scripts/runtime_safety_score.py --input examples/runtime-safety/sample-runtime-safety-snapshot.json
python3 scripts/runtime_safety_check.py --json
python3 scripts/generate_runtime_safety_report.py --input examples/runtime-safety/sample-runtime-safety-snapshot.json
```

Aggregated gate:

```bash
make runtime-safety-check
```

## Boundaries

This phase **does not** change billing, ledger persistence, database schemas, or enforcement semantics for `VALID` / `INVALID` / `BLOCKED`. Snapshots are **operator-controlled evidence aids**, not legal certifications.

## Further reading

- [Guardrails architecture](guardrails-architecture.md)
- [Human oversight](human-oversight.md)
- [Escalation policies](escalation-policies.md)
- [Override governance](override-governance.md)
- [Runtime risk management](runtime-risk-management.md)
- [Safety monitoring](safety-monitoring.md)
- [Runtime safety report generator](runtime-safety-report.md)
