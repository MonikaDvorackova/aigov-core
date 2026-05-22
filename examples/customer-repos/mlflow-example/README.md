# GovAI + MLflow (example customer pattern)

## Target user

MLOps engineers who already track **experiment metadata** in MLflow and want **external, tamper-evident** governance over which runs may promote to production models.

## Scenario

Training jobs log metrics and parameters to MLflow. A promotion pipeline:

1. Selects a candidate run based on business metrics.
2. Emits GovAI evidence tying the MLflow **`run_id`** (or artefact digest) to policy checks.
3. Requires explicit approval before the model registry transition to **Production**.

## Architecture

```text
MLflow tracking server
  -> training / evaluation jobs
  -> promotion workflow (CI or orchestrator)
  -> GovAI evidence + compliance summary
  -> model registry stage change (only if VALID)
```

## How GovAI is used

- Provides an **append-only audit trail** independent of MLflow’s own UI edits (depending on MLflow deployment hardening).
- Aligns **digest continuity** between exported artefacts and recorded events.

## Expected evidence pack flow

1. Record training completion with artefact digests (weights, ONNX, container image ref).
2. Record evaluation completion referencing the same digest lineage.
3. Record approval and promotion with actor identity and policy version.

## Compliance gate narrative

The gate answers: **“Is this MLflow run eligible for production under our AI governance policy?”** Invalid evaluation metadata or missing approvals maps to **`INVALID`** or **`BLOCKED`** per your configured rules — not silently overridden here.

## Commands (pseudo-commands)

```bash
export GOV_RUN_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
# Map MLflow run URI or artefact digest into your evidence payload JSON.
govai emit --run-id "$GOV_RUN_ID" --event-type training_completed --payload @mlflow_train_bundle.json
govai check --run-id "$GOV_RUN_ID"
```

## Non-goals

- No bundled MLflow server or tracking database.
- GovAI does not replace MLflow experiment search; it **gates** promotion using recorded evidence.
