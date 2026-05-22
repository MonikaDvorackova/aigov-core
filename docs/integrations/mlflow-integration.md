# MLflow integration guide

## Purpose

Explain how teams using **MLflow** for experiment tracking can **link training and evaluation runs** to GovAI evidence and compliance summaries—useful when ML governance policies require audit trails alongside metric artefacts.

## Integration overview

MLflow records **parameters, metrics, and artefacts** in its tracking store. GovAI records **governance evidence** and returns a **verdict** for a `run_id`. Integration is a **bridge**:

- When starting an MLflow run, allocate or reuse a GovAI `run_id` and store it as an MLflow tag (for example `govai.run_id`).
- After critical steps (data signing, evaluation harness, export approvals), POST evidence to GovAI with that `run_id`.
- In deployment jobs, read the tag, call `GET /compliance-summary`, and gate promotion on `VALID`.

Neither system replaces the other: MLflow is not a legal audit ledger; GovAI is not an experiment metric database.

## Implementation steps

1. **Tag at run start** — `mlflow.set_tag("govai.run_id", str(uuid4()))` (or operator-provided ID scheme).
2. **Emit evidence after milestones** — training completion, bias scan, model card publication—map each to a GovAI event payload your policy understands.
3. **Model registry promotion** — before transitioning an MLflow model stage to Production, invoke `govai check` using the tagged `run_id`.
4. **Artefact binding** — if you use digest manifests for ML artefacts, store them where your composite CI action expects (`docs/github-action.md`).
5. **Access control** — MLflow and GovAI credentials should use separate RBAC; do not reuse API keys across systems.

## Validation

- `python3 scripts/developer_integrations_check.py` for docs/examples presence.
- In a notebook or job, assert MLflow tags round-trip and `govai check` returns exit `0` on a dev stack.
- For offline interchange checks on model cards encoded as JSON artefacts, use interchange validators where applicable.

## Failure modes

- **Tag drift** — MLflow run restarted without copying `govai.run_id`. Mitigation: enforce tag presence in your training template job.
- **False linkage** — multiple concurrent experiments share one GovAI `run_id`. Mitigation: one-to-one mapping policy per MLflow run UUID.
- **Metric-only mindset** — believing high MLflow metric scores satisfy governance. Mitigation: treat GovAI verdict and policy modules as orthogonal evidence requirements.
