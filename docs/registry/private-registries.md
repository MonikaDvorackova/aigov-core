# Private registries

Operators often need a **catalog that mirrors the public registry JSON** while listing **internal** packs, schemas, and signing keys. GovAI supports this pattern as **documentation and layout**; hosted configuration is operator-specific.

## Recommended layout

- **Git repository (private fork)** — same `registry/` and `scripts/registry_check.py` with additional JSON files validated by a thin wrapper script.
- **Object storage index** — immutable JSON documents versioned by path; CI jobs pull and validate before promotion.
- **Package registry** — tarball releases with detached signatures; manifests list digest, capability ids, and interchange versions.

## Validation

Reuse `scripts/registry_check.py` patterns: private catalogs should keep **compatible `schema_version` values** or fork the script with a new catalog kind that remains explicit.

## Isolation guarantees

Private registries must **not** weaken public CI gates. Changes that affect shared validators or verdict semantics belong in the public repository’s review process unless the operator has intentionally forked the product.

## Linkage to policy packs

Internal packs can reuse the same `govai.policy_pack.policy_module` layout as [`../../examples/marketplace/`](../../examples/marketplace/) while pointing `policy_module_path` at internal-only JSON not shipped publicly.
