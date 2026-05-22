# Regulator export guide

## Purpose

`scripts/generate_regulatory_evidence_export.py` emits a **single deterministic Markdown** document from:

- `docs/regulatory/regulatory-evidence-manifest.json`
- the obligations file referenced by `obligations_index` (default `docs/regulatory/ai-act-obligations.json`)

The export is suitable as a **technical appendix** when legal teams approve its use. It is generated with **stable section order** and **sorted** lists where order is not semantically meaningful.

## Usage

```bash
python3 scripts/generate_regulatory_evidence_export.py \
  --manifest docs/regulatory/regulatory-evidence-manifest.json

python3 scripts/generate_regulatory_evidence_export.py \
  --manifest docs/regulatory/regulatory-evidence-manifest.json \
  --out /tmp/regulatory-evidence-export.md
```

## Determinism

- No timestamps are embedded in the Markdown body.
- Obligations and document lists are sorted by identifier or path.
- CI should archive stdout or `--out` for traceability alongside Git revision.

## Related JSON sample

See [../../examples/regulatory-evidence/sample-regulatory-export.json](../../examples/regulatory-evidence/sample-regulatory-export.json) for a structured analogue useful for integrations that consume JSON instead of Markdown.
