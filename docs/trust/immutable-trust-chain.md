# Immutable trust chain

This page describes how **cryptographic continuity** complements GovAI’s append-only audit ledger. It does **not** replace ledger enforcement or change compliance verdict semantics (`VALID`, `INVALID`, `BLOCKED`).

## Layers

1. **Ledger narrative** — tenant-scoped append events with server-side policy evaluation (canonical product behaviour).
2. **Evidence packs and exports** — interchange JSON and digests described in standards and evidence documentation.
3. **Optional signing layer** — detached signatures (for example JWS) over **canonicalised** payloads, anchored in your PKI.

## Trust anchors

Operators define **root keys** and **issuance paths** (`kid` relationships) in machine-readable form under `trust/trust-chain-example.json` and validate them with `scripts/trust_chain_check.py`. Anchors are organisation-specific; the repository ships **examples only**.

## Verification stance

Consumers should:

- Recompute the **payload digest** using the declared canonicalisation rules (`trust/signing-profile.json`).
- Validate **signatures** against published keys or certificates bound to `kid` values.
- Check that **signing and verification profile identifiers** match the organisation’s approved policy.

See [verification-workflows.md](verification-workflows.md) for a stepwise consumer checklist.

## Relationship to GovAI verdicts

Cryptographic verification of a signed artefact can still yield **INVALID** at the GovAI layer if policy or evidence requirements fail. Signing proves **origin and integrity of a blob**; GovAI proves **governance eligibility** for a `run_id`.
