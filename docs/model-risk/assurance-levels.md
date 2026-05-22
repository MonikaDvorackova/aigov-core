# Assurance levels

`scripts/model_risk_score.py` maps the composite **model_risk_score** (0–100) to an **assurance_level** label:

| Level | Composite range | Intended use |
| --- | --- | --- |
| `L3` | ≥ 85 | Strong offline evidence across pillars |
| `L2` | 70 – 84 | Meets baseline with tracked gaps |
| `L1` | 55 – 69 | Elevated risk; expand eval before scale |
| `L0` | < 55 | Do not treat as promotion-ready |

The boolean **`ok`** field is stricter: it additionally requires minimum pillar scores, zero diagnostic failures, and bounded warnings. See `scripts/model_risk_score.py` for the exact contract.

## Human review

Labels support communication; **organizational sign-off** remains outside this repository.
