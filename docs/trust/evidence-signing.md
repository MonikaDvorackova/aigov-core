# Evidence signing

Evidence packs aggregate governance artefacts for auditors and downstream systems. **Signing** binds a canonical digest of that pack to one or more keys without altering GovAI’s internal verdict computation.

## Canonical payload

Use a stable serialisation before hashing:

- Prefer **JSON canonicalisation** aligned with RFC 8785 semantics where practical (`trust/signing-profile.json` references `application/json+rfc8785`).
- Record the digest algorithm next to the digest (for example `SHA-384`).

## What to sign

Typical payloads include:

- Normalised evidence pack JSON (excluding signature blocks).
- Registry submission documents.
- Exported governance summaries intended for third-party auditors.

## Algorithms

Allowed combinations are enumerated in `trust/signing-profile.json` and `trust/verification-profile.json`. The repository validator rejects unknown JOSE or digest algorithms.

## Operational notes

- Sign **after** deterministic ordering of object keys in JSON sources.
- Store **detached** signatures alongside the pack so verifiers can recompute the digest from raw bytes.
- Never embed **private key material** in repositories or CI logs.

See [private-key-governance.md](private-key-governance.md) and [examples/trust/](../../examples/trust/README.md) for sample shapes.
