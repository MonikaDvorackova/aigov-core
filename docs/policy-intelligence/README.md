# Policy intelligence and governance control plane

This directory defines the **policy intelligence** layer for GovAI: how policy coverage is represented, how control maturity and governance gaps are scored from structured snapshots, and how deterministic reports support human review.

## Machine-readable index

- [`policy-intelligence-manifest.json`](policy-intelligence-manifest.json) — canonical manifest (validated by `scripts/validate_policy_intelligence_manifest.py`).

## Topics

| Topic | Document |
|-------|-----------|
| Coverage | [`policy-coverage.md`](policy-coverage.md) |
| Control maturity | [`control-maturity.md`](control-maturity.md) |
| Gap analysis | [`governance-gap-analysis.md`](governance-gap-analysis.md) |
| Risk-weighted controls | [`risk-weighted-controls.md`](risk-weighted-controls.md) |
| Reporting | [`control-plane-reporting.md`](control-plane-reporting.md) |
| Review workflow | [`policy-review-workflow.md`](policy-review-workflow.md) |
| Non-goals | [`governance-non-goals.md`](governance-non-goals.md) |

## Tooling (repository root)

- Diagnostics: `make policy-intelligence` or `python3 scripts/policy_intelligence_check.py --json`
- Manifest validation: `make policy-intelligence-manifest`
- Snapshot validation: `make governance-control-snapshot`
- Scoring: `make policy-coverage-score`
- Markdown report: `make governance-control-report`
- Aggregate gate: `make policy-intelligence-check`

## Examples

See [`../../examples/policy-intelligence/README.md`](../../examples/policy-intelligence/README.md).
