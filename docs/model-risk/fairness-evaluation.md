# Fairness evaluation

Fairness evaluation summarises **maximum group metric delta** and **fairness evaluation coverage** without storing sensitive attributes in this repository’s sample artifacts.

## Signals

| Field | Meaning |
| --- | --- |
| `max_group_metric_delta_percent` | Largest observed disparity across evaluated groups |
| `fairness_eval_coverage_percent` | Share of intended fairness scenarios exercised |

## Practices

- Keep raw evaluation tables in operator-controlled stores; snapshots should carry **aggregates only**.
- Refresh snapshots when cohort definitions or metrics change.

## Related

- [Evaluation planning](evaluation-planning.md)
- [Assurance levels](assurance-levels.md)
