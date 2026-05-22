# Evidence quality examples (Phase 19)

Offline-only examples for dataset provenance snapshot validation, scoring, and governance Markdown generation.

| Path | Purpose |
|------|---------|
| [`sample-dataset-provenance-snapshot.json`](sample-dataset-provenance-snapshot.json) | Canonical snapshot validated by `scripts/validate_dataset_provenance_snapshot.py`. |
| [`run-evidence-quality-check.sh`](run-evidence-quality-check.sh) | Emits aggregated diagnostics JSON (`evidence_quality_check.py --json`). |
| [`run-evidence-quality-score.sh`](run-evidence-quality-score.sh) | Emits deterministic scoring JSON for the sample snapshot. |
| [`run-dataset-governance-report.sh`](run-dataset-governance-report.sh) | Prints deterministic Markdown for the sample snapshot. |

## Documentation

See [`../../docs/evidence-quality/README.md`](../../docs/evidence-quality/README.md) for the manifest and conceptual overview.
