# Model assurance report

`scripts/generate_model_assurance_report.py` emits a **deterministic Markdown** document from a single evaluation snapshot plus manifest-derived weights.

## Sections

Reports include, in stable order:

1. Title and generator disclaimer
2. Snapshot metadata
3. Model identifiers
4. Assurance scores (`ok`, composite, pillar scores, `assurance_level`)
5. Findings and recommendations (sorted)
6. Per-pillar snapshot fields (sorted keys)
7. Diagnostics block
8. Reference paths

## Usage

```bash
python3 scripts/generate_model_assurance_report.py --input examples/model-risk/sample-model-evaluation-snapshot.json
python3 scripts/generate_model_assurance_report.py --input examples/model-risk/sample-model-evaluation-snapshot.json --out /tmp/report.md
```

## Boundaries

Reports are **not** EU AI Act technical documentation replacements and do not modify GovAI runtime enforcement.
