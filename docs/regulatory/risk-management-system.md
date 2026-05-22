# Risk management system

Article 9 requires a **risk management system** applied throughout the lifecycle of high-risk AI systems. GovAI supports **traceability and control evidence**, not the substantive risk analysis itself.

## Technical hooks

- **Policy at ingest** — evidence is evaluated when recorded; failures surface as **INVALID** or missing evidence as **BLOCKED** depending on configuration.
- **Portable standards** — interchange packs and validators (`docs/standards/`, `python/aigov_py/standards/`) let teams document control intent **offline** before binding to audit runs.
- **Manifest discipline** — `regulatory-evidence-manifest.json` ties documentation paths to automated checks so drift is visible in CI.

## What you must still do

- Identify reasonably foreseeable misuses and failure modes for **your** system in its **intended** operational context.
- Document mitigation, residual risk, and post-market feedback loops in your risk file.

Cross-reference: [ai-act-obligations.json](ai-act-obligations.json) obligation `ai_act_article_9_risk_management_system`.
