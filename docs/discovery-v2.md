---
title: Discovery v2 (deterministic, context-aware)
audience: customers, operators
scope: docs-only
---

## What Discovery v2 is

Discovery v2 is a **deterministic repository scan** that produces **context signals** used to:

- explain what GovAI thinks is happening in a repo (context awareness), and
- deterministically derive **additional `required_evidence`** (policy binding layer), without changing core decision semantics.

Discovery v2 is **not** a model safety evaluator and does not make “safe/unsafe” claims.

---

## Deterministic guarantees

Discovery v2 is designed to be production-safe and reproducible:

- **No randomness**: no sampling, no probabilistic scoring.
- **No ML**: no classifiers, no LLM calls, no embeddings.
- **Heuristic-only**: string/manifest/file-extension checks.
- **Bounded scanning**: ignores known large/vendor directories and caps per-file read size.

If a signal is emitted, it is because a deterministic signature was present (dependency manifests, import statements, framework keywords, file extensions, or dataset headers).

---

## What is detected (signals)

Discovery v2 emits the following top-level signals:

- **`ai_detected`**: any supported AI-related signal was found.
- **`llm_used`**: LLM SDK usage detected via dependency manifests and/or code signatures.
- **`model_types`**: a flat list containing any of:
  - `llm`
  - `classifier`
  - `embedding`
- **`user_facing`**: user-facing exposure signals (API endpoints / web frameworks / frontend hooks) detected via deterministic code signatures.
- **`pii_possible`**: likely PII columns detected in lightweight dataset header/schema scans (CSV header row; Parquet schema if available).
- **`external_dependencies`**: normalized list of external AI dependencies (example: `openai`, `anthropic`, `transformers`).

Example output shape:

```json
{
  "ai_detected": true,
  "llm_used": true,
  "model_types": ["llm"],
  "user_facing": true,
  "pii_possible": true,
  "external_dependencies": ["openai"]
}
```

---

## What is NOT detected

Discovery v2 intentionally does **not** do the following:

- no model “quality” or “safety” analysis
- no scoring, risk ranking, or probabilistic inference
- no attribution like “this model is compliant / non-compliant”
- no runtime monitoring or drift analysis (future roadmap only)
- no deep inspection of proprietary model artifacts (beyond deterministic filename/extension hints)

If you need model evaluation, that is **evidence** you generate and submit (for example `evaluation_reported`), not something GovAI infers.

---

## How this differs from AI analysis tools

Tools that analyze models or prompts attempt to judge model behavior and quality.

GovAI Discovery v2 is different:

- it is **context detection**, not evaluation
- it only emits **deterministic signals**
- those signals feed a deterministic mapping that results in a **flat `required_evidence` set**

See also: `docs/reports/discovery-v2-and-policy-binding.md`.

