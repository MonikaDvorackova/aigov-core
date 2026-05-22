# GovAI standards and policy pack registry (Phase 15)

This directory holds **deterministic, versioned JSON catalogs** that describe GovAI’s portable governance interchange, curated example policy packs, benchmark metadata, certification levels, and the capability taxonomy used for ecosystem documentation.

## Files

| File | Purpose |
| --- | --- |
| [`standards-catalog.json`](standards-catalog.json) | Interchange standards (`governance_evidence_pack`, `governance_policy_module`, `governance_decision_trace`) with on-disk schema paths. |
| [`policy-pack-catalog.json`](policy-pack-catalog.json) | Curated policy pack entries with certification level and capability tags (cross-linked to other catalogs). |
| [`benchmark-catalog.json`](benchmark-catalog.json) | Local benchmark suites (documentation and stdlib runners). |
| [`certification-levels.json`](certification-levels.json) | Community, verified, and enterprise certification metadata (documentation-oriented; not a legal claim). |
| [`capability-taxonomy.json`](capability-taxonomy.json) | Capability categories for mapping packs and submissions to governance themes. |

## Validation

From the repository root:

```bash
python3 scripts/registry_check.py
make registry-check
make customer-analytics-check
```

The checker validates JSON shape, required fields, **unique `id` values** within each catalog, **cross-references** between catalogs, and **on-disk paths** for schemas, manifests, and benchmark assets.

## Relationship to runtime enforcement

These catalogs are **documentation and interchange discoverability** only. They do **not** change Rust runtime policy enforcement, database migrations, or hosted **`GET /compliance-summary`** verdict semantics. Authoritative interchange bindings remain in `docs/standards/registry.md`, `python/aigov_py/standards/registry.py`, and the JSON Schemas under `schemas/`.

## Related documentation

- Registry program overview: [`../docs/registry/overview.md`](../docs/registry/overview.md)
- Submission workflow: [`../docs/registry/submission-guidelines.md`](../docs/registry/submission-guidelines.md)
- Certification program: [`../docs/registry/certification-program.md`](../docs/registry/certification-program.md)
- Policy pack marketplace (curated manifest): [`../marketplace/manifest.json`](../marketplace/manifest.json)
