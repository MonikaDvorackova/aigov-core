# Experiments

Offline evaluation and replay harnesses for GovAI research artefacts. Outputs are not part of the production audit service.

## Canonical vs generated

| Kind | Location | Committed? |
| --- | --- | --- |
| Drivers and READMEs | `experiments/*/` (for example `auditability/`) | Yes |
| Golden replay corpus used by tests | `experiments/output/artifact_bundle_replay_artifacts/` | Yes |
| Per-run replay trees | `experiments/output/artifact_bundle_replay_artifacts/**/rep_*/` | No |
| Regenerated scratch outputs | `experiments/output/.regenerated/` | No |

## `experiments/output/`

The `output/` tree contains a tracked replay corpus under `artifact_bundle_replay_artifacts/`, consumed by `python/tests/test_artifact_bundle_replay.py`. Do not delete or rewrite this corpus in incidental pull requests.

For new local replay runs, regenerate outside Git or use ignored paths (`experiments/output/artifact_bundle_replay_artifacts/**/rep_*/` and `experiments/output/.regenerated/`) so transient outputs are not committed accidentally.

## Production path

Operators and integrators should rely on `rust/`, `dashboard/`, `docs/hosted/`, and `make gate` for production validation and deployment. Experiment folders are optional research and validation tooling, not product contracts.
