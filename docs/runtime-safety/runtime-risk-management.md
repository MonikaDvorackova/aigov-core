# Runtime risk management

Runtime risk management connects **live signals** (guardrails, queues, drills) to **risk levels** used for promotion and incident decisions.

## Using Phase 21 scores

`scripts/runtime_safety_score.py` emits:

- Subscores for guardrails, escalation, human oversight, and override readiness.
- A weighted **runtime_safety_score** with diagnostics penalty.
- A **risk_level** label: `low`, `medium`, `high`, or `critical`.

Scores are **deterministic** given a snapshot; they support CI artefacts and diffable reviews.

## Operational loop

1. Capture a snapshot window from staging or production telemetry.
2. Validate with `validate_runtime_safety_snapshot.py`.
3. Score and archive JSON output next to the snapshot.
4. For leadership review, generate Markdown with `generate_runtime_safety_report.py`.

## Limits

Scores do not prove absence of failure; they structure evidence for humans who remain accountable for go / no-go decisions.
