# Data minimization patterns

Minimisation reduces privacy risk and storage growth while preserving auditability of **governance-relevant** facts.

## Patterns

1. **Field allowlists** — only permitted keys in evidence JSON pass schema validation.
2. **Hashed identifiers** — store salted hashes of user or customer identifiers where correlation must be limited.
3. **Aggregated metrics** — emit rollups instead of raw prompts when policy allows.
4. **Separate sensitive annexes** — keep high-sensitivity payloads outside default exports with tighter RBAC.

## Policy linkage

Required evidence items can mandate minimised artefacts (for example signed digests of datasets instead of raw rows).

## Related

- `docs/privacy/privacy-architecture.md`
- `docs/privacy/retention-policy-patterns.md`
