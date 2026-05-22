# Regulatory evidence platform (EU AI Act mapping)

This directory contains **documentation**, **machine-readable manifests**, and **cross-links** to executable validators under `scripts/`. The layer helps operators assemble **technical evidence narratives** aligned with EU Artificial Intelligence Act themes. It does **not** provide legal advice, statutory interpretation, or conformity decisions.

```docs
preset: regulatory-matrix
```

## Contents

| File | Purpose |
|------|---------|
| [regulatory-evidence-manifest.json](regulatory-evidence-manifest.json) | Canonical index of documents, themes, operational probes, and required checks |
| [ai-act-obligations.json](ai-act-obligations.json) | Structured obligation rows with evidence paths into this tree |
| [ai-act-mapping.md](ai-act-mapping.md) | How GovAI artefacts map *indicatively* to AI Act chapters |
| [high-risk-system-obligations.md](high-risk-system-obligations.md) | High-risk system themes and non-claims |
| [conformity-assessment.md](conformity-assessment.md) | Using exports alongside conformity workflows |
| [evidence-obligations.md](evidence-obligations.md) | Matrix linking obligations to repository evidence |
| [technical-documentation.md](technical-documentation.md) | Technical file expectations (Annex IV–informed, not a legal template) |
| [human-oversight.md](human-oversight.md) | Human oversight design notes for operator-run deployments |
| [risk-management-system.md](risk-management-system.md) | Risk management system narrative vs audit evidence |
| [post-market-monitoring.md](post-market-monitoring.md) | Post-market monitoring hooks and exports |
| [regulator-export-guide.md](regulator-export-guide.md) | How to produce and review regulator-facing Markdown |

## Executable checks

From the repository root:

```bash
make regulatory-manifest
make ai-act-obligations
make regulatory-evidence
make regulatory-export
make regulatory-check
```

JSON diagnostics:

```bash
python3 scripts/regulatory_evidence_check.py --json
python3 scripts/validate_regulatory_evidence_manifest.py --json
python3 scripts/validate_ai_act_obligations.py --json
```

Deterministic Markdown export:

```bash
python3 scripts/generate_regulatory_evidence_export.py --manifest docs/regulatory/regulatory-evidence-manifest.json
```

See also [`../../examples/regulatory-evidence/README.md`](../../examples/regulatory-evidence/README.md).
