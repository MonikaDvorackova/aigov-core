# Technical documentation (Annex IV–informed)

Annex IV of the EU AI Act lists **elements** of technical documentation for high-risk AI systems. GovAI does not ship a completed Annex IV template; it ships **discipline** for traceable technical narratives:

- **Versioned manifests** under `docs/regulatory/` consumed by validators.
- **Deterministic exports** combining manifests and obligation metadata.
- **Audit exports** from the hosted or self-hosted service (`GET /api/export/:run_id`) as **runtime** evidence, separate from this static layer.

## Suggested mapping practice

1. Maintain your statutory Annex IV dossier in your QMS / PLM system of record.
2. Use GovAI exports as **annexes** where they evidence controls (for example approval gates, policy versions, run digests).
3. Record manifest digests (for example Git tree hash at release) in your change record.

See [regulator-export-guide.md](regulator-export-guide.md) for the Markdown generator contract.
