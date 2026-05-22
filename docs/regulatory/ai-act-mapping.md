# EU AI Act mapping (indicative)

GovAI is an **audit-backed decision system**: it records structured lifecycle events, evaluates policy at ingest, and exposes a single compliance verdict per run. The EU **Artificial Intelligence Act** imposes obligations on **providers** and **deployers** of AI systems, with additional measures for **high-risk** systems listed in Annex III.

## What this mapping is

- **Indicative** — it relates GovAI concepts (evidence, bundles, exports, approvals) to **themes** in the AI Act so technical teams can navigate documentation.
- **Non-authoritative** — it does not determine whether your deployment is high-risk, limited risk, or minimal risk under EU law.

## What GovAI supplies

- **Append-only evidence** suitable for attachment to internal technical files.
- **Deterministic validators** for repository manifests (`scripts/validate_regulatory_evidence_manifest.py`, `scripts/validate_ai_act_obligations.py`).
- **Regulator-facing Markdown export** (`scripts/generate_regulatory_evidence_export.py`) built from the same manifests your CI can snapshot.

## What remains with counsel and notified bodies

- Legal characterisation of the system (including GPAI with systemic risk, where applicable).
- Completeness of Annex IV technical documentation.
- Conformity assessment outcomes and EU declaration of conformity.

For the obligation index consumed by tooling, see [ai-act-obligations.json](ai-act-obligations.json) and [evidence-obligations.md](evidence-obligations.md).
