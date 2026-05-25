# Signed Evidence Bundle Verification

## Summary

Adds Ed25519 signing and verification for `aigov.audit_export.v1` exports: a deterministic canonical signing payload, integrity checks (schema, `run_id`, `events_content_sha256`, `bundle_sha256`, verdict binding), CLI commands `govai sign-audit-export` and `govai verify-audit-export`, and unit tests for valid and tampered documents. Ledger append-only semantics and runtime projection are unchanged; signing is post-export only.

## Evaluation gate

Evaluation evidence in signed exports remains **ledger-authoritative**. The signing payload binds `decision_verdict` and `events_content_sha256` as produced by export projection at sign time. Verification recomputes the events digest from `evidence_events` and rejects tampering that would misrepresent evaluation outcomes without invalidating the signature. Signing does not override `evaluation_passed` or compliance rules on the server.

## Human approval gate

Human approval state in signed exports remains **ledger-authoritative**. The canonical payload includes `decision_verdict` (which reflects approval and promotion prerequisites in projection). Tampering with `human_approved` evidence in the export without updating hashes or re-signing fails `events_content_sha256` or signature verification. Optional `human_approval` fields in export JSON are covered by the events digest, not a separate side channel.

## Cryptographic verification

- **Algorithm:** Ed25519 detached signature over SHA-256 hex digest of canonical JSON preimage
- **Preimage fields:** `schema_version`, `run_id`, `policy_version`, `environment`, `bundle_sha256`, `events_content_sha256`, `chain_head_record_sha256`, `decision_verdict`
- **Trust:** `issuer_id` + `pubkeys_base64` list (same JSON env as policy bundle trust)
- **Failure modes:** unsupported schema, run_id mismatch, event digest mismatch, invalid bundle hash format, digest/signature mismatch, unknown issuer or wrong public key

## Verification

```bash
make gate
make reconstructible-demo-check
make reference-integrations-check
make core-runtime-examples-check
cd python && python -m pytest tests/test_audit_export_signing.py -q
cd ../rust && cargo build --locked --bin aigov_audit && cargo test --locked
```

Operator flow:

```bash
govai export-run --run-id "$GOVAI_RUN_ID" > export.json
govai sign-audit-export --in export.json --out export.signed.json ...
govai verify-audit-export --path export.signed.json
```
