# Runtime safety report generator

`scripts/generate_runtime_safety_report.py` assembles a **deterministic Markdown** report from:

- A validated runtime safety snapshot JSON, and
- Scores produced by `scripts/runtime_safety_score.py` (same weighting rules as CI).

## Usage

```bash
python3 scripts/generate_runtime_safety_report.py \
  --input examples/runtime-safety/sample-runtime-safety-snapshot.json \
  --manifest docs/runtime-safety/runtime-safety-manifest.json \
  --out /tmp/runtime-safety-report.md
```

## Output sections

The report includes snapshot metadata, scores, per-domain tables, diagnostics, findings, recommendations, and paths for traceability.

## Stability

Sections and bullet keys are emitted in **sorted order** where applicable so that repeated runs produce identical Markdown for the same inputs.
