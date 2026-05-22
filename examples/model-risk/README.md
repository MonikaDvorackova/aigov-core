# Model risk examples

Deterministic **stdlib** examples for Phase 20: validate the manifest, validate a snapshot, score risk, and generate an assurance Markdown report.

## Prerequisites

Repository root, Python 3.10+.

## Scripts

```bash
./examples/model-risk/run-model-risk-check.sh
./examples/model-risk/run-model-risk-score.sh
./examples/model-risk/run-model-assurance-report.sh
```

Or use Make:

```bash
make model-risk-assurance-check
```

## Files

| File | Role |
| --- | --- |
| [`sample-model-evaluation-snapshot.json`](sample-model-evaluation-snapshot.json) | Canonical sample snapshot for CI and local scoring |
| `run-model-risk-check.sh` | Aggregated diagnostics JSON to stdout |
| `run-model-risk-score.sh` | Composite score JSON to stdout |
| `run-model-assurance-report.sh` | Markdown report to stdout |

## Documentation

See [`../../docs/model-risk/README.md`](../../docs/model-risk/README.md).
