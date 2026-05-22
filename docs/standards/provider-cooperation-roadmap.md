# Provider cooperation and standards roadmap

Generative AI governance fails when **providers withhold** model lineage, safety evaluations, or usage metadata. GovAI addresses this with **portable standards**, explicit **registry** artefacts, and **fallback** strategies documented alongside interchange validators.

## Stable identifiers

- **Model and policy identifiers** should use immutable, versioned URNs or digests referenced in evidence packs (`docs/standards/registry.md`, `schemas/`).

## Metadata schemas

- Interchange JSON under `python/aigov_py/standards/` defines structural expectations; validators are deterministic and offline-capable.

## Attestation APIs (concepts)

See `docs/standards/attestation-api-concepts.md` for conceptual read-only attestation surfaces (health, model card digests, evaluation summaries). Concrete vendor APIs evolve independently of GovAI releases.

## Third-party monitoring

- Independent evaluators, red-team partners, or regulators may consume **exports** and **bundle hashes** without write access to the ledger.

## Roadmap posture

- Prefer **published** interchange specs and **versioned** policy packs over ad-hoc JSON.
- Expand marketplace catalog entries (`marketplace/manifest.json`) as community packs mature.

## Related

- `docs/standards/attestation-api-concepts.md`
- `docs/standards/fallback-strategies.md`
- `docs/standards/interchange-specification.md`
