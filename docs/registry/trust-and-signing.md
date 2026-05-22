# Trust, signing, and provenance

GovAI separates **three trust layers** so integrators do not confuse interchange validation with deployment authority.

## Layers

1. **Structural validation** — JSON Schema and Python validators confirm shape and digest stability for portable artefacts.
2. **Registry metadata** — catalogs document where artefacts live, who maintains them, and which capabilities they cover.
3. **Operational provenance** — signatures, SBOM references, and build attestations bind **specific bytes** to **specific releases**.

## Signing concepts (documentation)

- **Publisher signature** — a detached signature over a policy pack tarball or manifest digest, produced by a maintainer key listed in private registry configuration.
- **Transparency log (optional)** — an append-only witness log recording release digests; useful for enterprise adoption even when GovAI itself is not a log operator.
- **CI attestation** — workflow artefacts (for example JSON outputs under `.oss-ci-out/` in CI documentation) show **what ran**, not **who approved** a production deployment.

Signing policies belong in operator docs; the public repo documents **shapes and examples** only.

## Relationship to GovAI audit exports

When a deployment binds to GovAI audit evidence, digests in `GET /api/export/:run_id` remain authoritative for that run. Registry signing does **not** replace export digests; it can **complement** them by attesting upstream pack contents.

## Further reading

- [`../marketplace/security-and-trust.md`](../marketplace/security-and-trust.md)
- [`../trust-model.md`](../trust-model.md)
