# Risk-weighted controls

Risk-weighted interpretation combines **gap severity** with **evidence attachment** flags so operators can sort controls into remediation queues. This layer is **advisory**: it does not re-rank audit verdicts or alter policy evaluation in the audit service.

## Heuristics

Offline tooling may emit findings such as missing evidence attachments when `evidence_attached` is false, even if `gap_severity` is `none`, because documentation drift is a governance signal distinct from incident severity.

## Determinism

Scoring and report generation use fixed formulas in `scripts/policy_coverage_score.py` so CI JSON and Markdown outputs are stable for the same input snapshot.

## Related

- [`governance-gap-analysis.md`](governance-gap-analysis.md)
- [`governance-non-goals.md`](governance-non-goals.md)
