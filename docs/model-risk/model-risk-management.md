# Model risk management

Model risk management for GovAI deployments ties **offline evaluation evidence** to promotion decisions. Operators maintain manifests and periodic evaluation snapshots; deterministic scripts validate structure and emit scores for CI and human review.

## Scope

- Documentation, manifests, snapshots, validators, scoring, and reports under Phase 20.
- Explicit **non-goals**: no model hosting, no training, no ledger or billing changes, no runtime enforcement semantic changes.

## Practices

1. **Version snapshots** with `snapshot_id`, `captured_at`, and `window_days` aligned to release candidates.
2. **Record four pillars** — evaluation fit, safety, robustness, fairness — with numeric fields the validators understand.
3. **Attach diagnostics** (`failure_count`, `warning_count`, `checks`) so `model_risk_score.py` can fail closed when failures are non-zero.
4. **Archive reports** alongside change tickets; treat assurance Markdown as engineering evidence, not a regulatory filing.

## Related

- [README](README.md) — index and Makefile targets.
- [Assurance levels](assurance-levels.md) — interpretation of `L0`–`L3`.
