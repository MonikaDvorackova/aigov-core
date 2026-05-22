# Human oversight

Article 14 of the EU AI Act requires that high-risk AI systems be designed and developed so that **natural persons can effectively oversee** their functioning during use. GovAI aligns at the **process** layer:

- **Documentation gates** — `docs/reports/*.md` in this repository require explicit **Evaluation gate** and **Human approval gate** sections for audit reports (`scripts/gate_reports.py`). That pattern models accountable sign-off in engineering workflows; it is **not** a substitute for deployer-side operational oversight.
- **Promotion semantics** — the evidence pipeline distinguishes states such as **BLOCKED** until prerequisites are met, mirroring the idea that automation must not bypass human judgment where your policy requires it.

## Operator responsibilities

- Define **who** may approve high-impact changes and **which** evidence must exist.
- Ensure **override** and **stop** procedures exist outside GovAI when the AI system can cause harm if left unchecked.

For deployer monitoring themes, see [evidence-obligations.md](evidence-obligations.md).
