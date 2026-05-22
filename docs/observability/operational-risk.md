# Operational risk

The operational health scoring tool derives a single **risk_level** from the sub-scores it computes for a given operational snapshot. The risk level is intended for offline review and for prioritising operator follow-up; it is **not** a verdict surface.

## Risk-level derivation

| Risk level | Conditions (all must hold) |
|------------|-----------------------------|
| `low`      | `health_score >= 85`, every sub-score `>= 75`, all readiness booleans `true` |
| `medium`   | `health_score >= 70` and every sub-score `>= 60` |
| `high`     | `health_score >= 50` (and one of the above failed) |
| `critical` | otherwise |

Sub-scores are computed by [`scripts/operational_health_score.py`](../../scripts/operational_health_score.py) for `runtime_health`, `readiness`, `evidence_flow`, and `diagnostics` independently and then combined using the weights in [`observability-manifest.json`](observability-manifest.json) (`score_weights`).

## Follow-up workflow

1. Run `make operational-health-score` after collecting a fresh snapshot.
2. Inspect `findings` — they enumerate the contributing factors (for example `runtime_health:error_rate_percent_above_threshold:7` or `diagnostics:failed_check:docs_links_strict`).
3. For `high` or `critical` levels, generate the full Markdown report with `make operational-intelligence-report` and circulate it for operator review.
4. Track remediations outside GovAI (issue tracker, runbooks). The snapshot tooling does not write back into the audit ledger.

## Non-claims

- Risk levels do not replace incident severity classifications used by the operator’s on-call runbooks.
- A `low` risk level is **not** a compliance attestation; it is a deterministic summary of the supplied snapshot only.
