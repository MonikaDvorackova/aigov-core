# MLflow + GovAI example

Bridge MLflow runs to GovAI using tags and promotion gates.

## Outline

1. `mlflow.start_run()` then `mlflow.set_tag("govai.run_id", "<uuid>")`.
2. After training or evaluation milestones, POST evidence to GovAI with the same UUID.
3. Before registry stage transition to Production, run `govai check --run-id <uuid>`.

## Docs

`docs/integrations/mlflow-integration.md`.
