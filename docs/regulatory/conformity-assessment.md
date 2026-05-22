# Conformity assessment (using GovAI exports)

**Conformity assessment** under the EU AI Act is a regulated procedure (internal production control, EU-type examination, full quality assurance, or other applicable modules). GovAI participates only as **supporting technical infrastructure**: reproducible exports and append-only audit history.

## How teams typically use GovAI artefacts

1. **Technical documentation appendix** — attach a frozen Markdown export from `scripts/generate_regulatory_evidence_export.py` when counsel agrees it adds traceability.
2. **Operational evidence** — cite `GET /compliance-summary` outcomes and evidence bundles for specific **runs** where those runs map to documented controls.
3. **Change control** — correlate Git revisions of `docs/regulatory/*.json` with release tags.

## Boundaries

- Notified Bodies and regulators evaluate **legal** sufficiency; repository validators enforce **schema and path** consistency only.
- Do not treat CI JSON artefacts as substitute dossier sections unless your quality system explicitly adopts them.

See [regulator-export-guide.md](regulator-export-guide.md) for export mechanics.
