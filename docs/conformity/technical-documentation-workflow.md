# Annex IV technical documentation workflow

The [`technical-documentation-workflow.json`](../../conformity/technical-documentation-workflow.json) artefact organizes the operator-internal process for preparing the Annex IV dossier required by Article 11 of the EU AI Act.

## Annex IV sections

The artefact enumerates sections such as system description, design and development, monitoring and logging, risk management, accuracy and robustness, post-market monitoring plan, and quality management. Each section lists `required_elements` and pointers to `evidence_sources` that may already exist in this repository (model cards, evaluation reports, dataset provenance snapshots, observability contracts).

## Lifecycle

`dossier_lifecycle` defines three preparation states (`draft`, `internal_review`, `frozen_for_declaration`) and the requirements for a frozen dossier (`version_locked`, `evidence_attachments_listed_by_path`, `approvals_recorded`). A minimum retention period (`retention_years_minimum`) is captured for cross-reference with operator records policy.

## Export hooks

`export_hooks` links to existing GovAI scripts that produce reproducible Markdown and JSON. Operators decide which exports to attach to the dossier; the workflow itself does not generate the dossier.

## Boundaries

Annex IV **legal sufficiency** is determined by counsel and competent authorities. GovAI artefacts function as appendices, not stand-alone Annex IV sections.
