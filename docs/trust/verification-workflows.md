# Verification workflows

Use this checklist when verifying signed governance artefacts **outside** the running audit service (for example in a secure review workstation or auditor VPC).

## Inputs

- Raw JSON payload (or exported file bytes).
- Detached signatures and declared `kid` values.
- `trust/signing-profile.json` and `trust/verification-profile.json` (or your organisation’s copies).

## Steps

1. **Parse JSON** — reject on schema drift before cryptography.
2. **Canonicalise** — apply the same rules the signer used (see [evidence-signing.md](evidence-signing.md)).
3. **Digest** — compute `SHA-256`, `SHA-384`, or `SHA-512` as declared; compare to `digest_hex` fields in attestation or signed-pack metadata.
4. **Verify signatures** — for each signature, resolve `kid` to a public key via your trust chain, then verify JWS (or equivalent) per `jose_alg`.
5. **Profile match** — assert `signing_profile_id` and `verification_profile_id` are approved for this environment.
6. **Replay GovAI checks** — if the artefact references a `run_id`, optionally call `GET /compliance-summary` in a read-only audit environment; cryptographic success does not imply `VALID`.

## Machine-readable result shape

See `examples/trust/sample-verification-result.json` for a minimal `verification_result` document suitable for automation and CI reporting.
