# Governance gap analysis

Gap analysis aggregates **per-control gap severity** labels from structured snapshots. Severities are coarse buckets (`none`, `low`, `medium`, `high`, `critical`) used only for **offline risk scoring** and prioritization in generated recommendations.

## Gap risk score

The **gap_risk_score** (0–100) is computed from weighted severities normalized by control count. Higher scores indicate more remediation work on paper; they do not automatically change runtime behavior.

## Using gaps in reviews

Teams should reconcile gap labels with actual incidents, audit findings, and change records. The snapshot format is intentionally simple so validators and CI artefacts stay deterministic.

## Related

- [`policy-review-workflow.md`](policy-review-workflow.md)
- [`control-plane-reporting.md`](control-plane-reporting.md)
