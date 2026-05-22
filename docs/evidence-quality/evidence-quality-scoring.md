# Evidence quality scoring

GovAI exposes **integer scores from 0 to 100** for provenance, lineage, and retention dimensions, plus a weighted **evidence_quality_score** and a categorical **risk_level** (`low`, `medium`, `high`). Scores are computed only from the JSON snapshot by `scripts/evidence_quality_score.py` without network access.

## Principles

- **Deterministic**: identical input bytes yield identical output JSON (sorted keys).
- **Advisory**: scores do not replace `GET /compliance-summary` verdicts or Rust policy checks.
- **Fail-closed on schema**: invalid snapshots return `ok: false`, zero scores, and `risk_level: high`.

## Dimensions

| Dimension | Meaning |
|-----------|---------|
| `provenance_score` | Source registration, checksum coverage, and governance approval block. |
| `lineage_score` | Declared lineage edges and transformation code references. |
| `retention_score` | Classification validity, day bounds, and legal-hold policy linkage. |

## Outputs

The scorer emits `findings` and `recommendations` as sorted lists of stable string tokens so CI and humans can diff reports across commits without nondeterministic prose.
