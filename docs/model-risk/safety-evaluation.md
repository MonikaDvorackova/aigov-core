# Safety evaluation

Safety evaluation focuses on **policy adherence**, **harmful-output test pass rates**, and **open red-team findings**. Phase 20 encodes these as numeric fields inside the evaluation snapshot; validators reject malformed payloads.

## Signals

| Field | Meaning |
| --- | --- |
| `policy_violation_rate_percent` | Estimated share of outputs violating policy in eval harness |
| `harmful_eval_pass_rate_percent` | Pass rate on curated harmful-output test sets |
| `red_team_findings_open` | Count of unresolved red-team issues |

## Interpretation

Higher `harmful_eval_pass_rate_percent` is better. Lower `policy_violation_rate_percent` and `red_team_findings_open` are better. Scoring applies deterministic penalties documented in `scripts/model_risk_score.py`.

## Related

- [Robustness evaluation](robustness-evaluation.md)
- [Model assurance report](model-assurance-report.md)
