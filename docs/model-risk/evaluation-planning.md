# Evaluation planning

Evaluation planning defines **what** to measure before a model or prompt bundle is promoted. GovAI Phase 20 snapshots capture **task fit**, **documentation completeness**, and **latency** as quantitative proxies for operational readiness.

## Checklist

- Identify primary tasks and acceptable latency budgets (`latency_p95_ms`).
- Set minimum documentation completeness expectations (`documentation_completeness_score`).
- Align `task_fit_score` with human review of sample outputs (offline).

## Snapshot fields

See `evaluation` in [`../../examples/model-risk/sample-model-evaluation-snapshot.json`](../../examples/model-risk/sample-model-evaluation-snapshot.json).

## Tooling

`scripts/validate_model_evaluation_snapshot.py` enforces required keys. `scripts/model_risk_score.py` applies deterministic penalties when scores fall below internal thresholds.
