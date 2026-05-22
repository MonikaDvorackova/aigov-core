# Evidence and obligations matrix

This page summarises how **machine-readable** obligation rows in [ai-act-obligations.json](ai-act-obligations.json) reference **Markdown** guides in this directory. CI validators ensure every `evidence_paths` entry exists on disk.

| Obligation id (excerpt) | Article (indicative) | Primary evidence doc |
|-------------------------|----------------------|----------------------|
| `ai_act_article_9_risk_management_system` | Article 9 | [risk-management-system.md](risk-management-system.md) |
| `ai_act_article_10_data_governance` | Article 10 | this matrix + governance packs (portable standards) |
| `ai_act_article_11_technical_documentation` | Article 11 | [technical-documentation.md](technical-documentation.md) |
| `ai_act_article_14_human_oversight` | Article 14 | [human-oversight.md](human-oversight.md) |
| `ai_act_article_43_conformity_assessment` | Article 43 | [conformity-assessment.md](conformity-assessment.md) |
| `ai_act_article_72_post_market_monitoring_by_providers` | Article 72 | [post-market-monitoring.md](post-market-monitoring.md) |

**Source of truth:** the JSON file is validated by `scripts/validate_ai_act_obligations.py`; this table may lag the JSON intentionally—when they diverge, CI fails on the JSON contract.
