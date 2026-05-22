# Model risk, evaluation, and assurance

Phase 20 adds **stdlib-only** tooling for model risk manifests, evaluation snapshots, deterministic scoring, aggregated diagnostics, and Markdown assurance reports. These artifacts support governance reviews; they are **not** legal conformity statements and do **not** change GovAI verdict semantics, billing, ledger storage, or database schemas.

## Machine-readable index

- [`model-risk-manifest.json`](model-risk-manifest.json) — schema for snapshots, score weights, referenced docs/examples, and operational probes.

## Operator guides

- [Model risk management](model-risk-management.md) — roles, evidence, and release alignment.
- [Evaluation planning](evaluation-planning.md) — offline evaluation design before promotion.
- [Safety evaluation](safety-evaluation.md) — policy, harmful-output, and red-team signals.
- [Robustness evaluation](robustness-evaluation.md) — perturbation and adversarial probes.
- [Fairness evaluation](fairness-evaluation.md) — group metrics and coverage.
- [Assurance levels](assurance-levels.md) — how composite scores map to `L0`–`L3`.
- [Model assurance report](model-assurance-report.md) — contract for generated Markdown.

## Tooling (repository root)

```bash
make model-risk                  # aggregated diagnostics (human table; use script --json)
make model-risk-manifest         # validate manifest
make model-evaluation-snapshot   # validate sample snapshot
make model-risk-score            # deterministic JSON scoring (sample)
make model-assurance-report      # Markdown report smoke
make model-risk-assurance-check               # aggregate gate + documentation headings gate
```

Example drivers: [`../../examples/model-risk/README.md`](../../examples/model-risk/README.md).
