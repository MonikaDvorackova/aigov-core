# Dataset governance report

`scripts/generate_dataset_governance_report.py` renders a deterministic Markdown report from a provenance snapshot. Sections include dataset identifiers, a scores table, owners, sources, lineage bullets, retention bullets, findings, recommendations, and a short lineage risk narrative.

## Usage

```bash
python3 scripts/generate_dataset_governance_report.py \
  --input examples/evidence-quality/sample-dataset-provenance-snapshot.json
```

Optional `--out path.md` writes UTF-8 text with LF newlines for CI capture.

## Determinism

Lists are sorted before emission so diffs stay stable across platforms with the same input JSON.
