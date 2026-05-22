# Conformity assessment workflow

The [`conformity-assessment-workflow.json`](../../conformity/conformity-assessment-workflow.json) artefact captures the operator-internal flow used to prepare an EU AI Act conformity assessment (Article 43) before any notified body interaction.

## Phases

| Phase | Intent |
| --- | --- |
| Scoping | Confirm intended purpose and the applicable assessment module. |
| Dossier preparation | Assemble Annex IV elements and reference reproducible exports where useful. |
| Internal control review | Verify QMS coverage and risk management currency. |
| Declaration and marking | Issue the EU declaration of conformity and apply CE marking. |
| Change control | Detect substantial modifications that require reassessment. |

Each phase lists objectives, expected inputs, outputs, and the human approvals that must be recorded. The artefact also enumerates **audit events** that operators should emit when their tooling supports it (for example `conformity.declaration.issued`).

## Applicability

The workflow is targeted at **high-risk AI systems** within scope of Annex III or those classified as safety components under Annex I. The artefact lists explicit out-of-scope notes (prohibited practices, separate general-purpose AI obligations).

## Evidence export hooks

The workflow points at existing GovAI scripts (`generate_regulatory_evidence_export.py`, `validate_ai_act_obligations.py`, `validate_regulatory_evidence_manifest.py`) so dossier preparation can attach reproducible Markdown and JSON exports. Counsel decides whether to include them.

## Governance boundaries

The artefact restates that GovAI does **not** issue declarations of conformity, interact with notified bodies, or judge legal sufficiency. Repository validators only check structural consistency.
