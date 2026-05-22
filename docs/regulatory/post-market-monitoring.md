# Post-market monitoring

Article 72 requires providers to establish a **post-market monitoring system** proportionate to the AI technologies in question. GovAI can contribute **technical telemetry** where operators connect monitoring to audit-backed services.

## Artefacts

- **Recurring compliance summaries** — `GET /compliance-summary` for configured runs (when your integration records them).
- **Evidence exports** — `GET /api/export/:run_id` bundles for investigations after incidents or drift reviews.
- **Repository diagnostics** — `scripts/regulatory_evidence_check.py --json` for integrity of regulatory documentation paths in CI.

## Limits

- GovAI does not perform pharmacovigilance-style safety surveillance for your domain.
- Statistical monitoring, incident triage, and regulatory reporting remain **operator-owned**.
