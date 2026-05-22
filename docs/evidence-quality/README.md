# Evidence quality and dataset governance

This folder defines the **Phase 19** machine-readable manifest, documentation contracts, and pointers to offline validators for dataset provenance snapshots. Outputs are deterministic JSON and Markdown suitable for CI artefacts and governance reviews; they remain **advisory** relative to audit-service enforcement.

## Contents

| File | Role |
|------|------|
| [`evidence-quality-manifest.json`](evidence-quality-manifest.json) | Canonical index validated by `scripts/validate_evidence_quality_manifest.py`. |
| [`evidence-quality-scoring.md`](evidence-quality-scoring.md) | How integer scores are derived from snapshot fields. |
| [`dataset-provenance.md`](dataset-provenance.md) | Required provenance fields and registration expectations. |
| [`data-lineage.md`](data-lineage.md) | Lineage edges and transformation references. |
| [`retention-policy.md`](retention-policy.md) | Retention classification, day counts, and legal hold references. |
| [`evidence-quality-gates.md`](evidence-quality-gates.md) | How documentation and CI gates use these artefacts. |
| [`dataset-risk.md`](dataset-risk.md) | Heuristic lineage risk levels and limitations. |
| [`dataset-governance-report.md`](dataset-governance-report.md) | Markdown report generator contract. |

## Quickstart

From the repository root:

```bash
make evidence-quality-check
```

Or run the example drivers under [`../../examples/evidence-quality/`](../../examples/evidence-quality/README.md).
