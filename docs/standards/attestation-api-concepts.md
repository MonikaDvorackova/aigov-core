# Attestation API concepts (read-only)

**Attestation**, in this document, means **cryptographically or procedurally anchored statements** about a model or service (version, evaluation digest, data card hash) suitable for binding to evidence events.

## Conceptual endpoints (not a mandatory protocol)

Illustrative surfaces operators may expose or consume:

| Surface | Purpose |
|---------|---------|
| `GET /.well-known/govai-model-card` | Discover model card URL and digest algorithm |
| `GET /attestations/{model_id}` | Signed JSON with digests of bundled evaluations |
| `POST /evidence` (consumer) | GovAI ingestion of attestation events referencing those digests |

## Binding to GovAI

- Evidence events may include **digest fields** referencing external attestation documents.
- `verify-evidence-pack` flows can require manifest alignment with hosted `bundle-hash` when configured.

## Non-goals

- GovAI does **not** mandate a single global attestation authority.
- No claim that a vendor implements these exact URLs.

## Related

- `docs/standards/provider-cooperation-roadmap.md`
- `docs/standards/fallback-strategies.md`
