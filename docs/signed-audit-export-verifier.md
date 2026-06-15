# Signed audit export verifier (offline)

GovAI Core ships a **Rust-native** verifier for signed audit export zip bundles. Auditors and downstream tooling can validate exports **without a running GovAI instance**.

## Command

```bash
# Build the verifier binary once
cd rust && cargo build --bin verify_audit_export_bundle_once && cd ..

# Trust store (Ed25519 public keys JSON array)
export AIGOV_POLICY_TRUST_ED25519_JSON="$(cat examples/signed-audit-export-bundle/trust-demo.json)"

# Structured JSON output (recommended)
govai verify-evidence-pack \
  --bundle examples/signed-audit-export-bundle/demo.valid.zip \
  --json
```

Human-readable output omits `--json`; exit code is **0** only when `overall_status` is `success`.

## Bundle layout

| Path | Role |
|------|------|
| `manifest.json` | `aigov.audit_export_bundle.v1` — file list, refs, canonical digest |
| `audit_export.json` | Signed `aigov.audit_export.v1` document |
| `evidence/…`, `findings/…` | Optional attachments referenced by manifest |

Regenerate the committed demo fixture (no runtime):

```bash
python3 scripts/generate_signed_audit_export_bundle_demo.py
```

See [`examples/signed-audit-export-bundle/README.md`](../examples/signed-audit-export-bundle/README.md).

## Structured output

The verifier returns an **`AuditExportVerificationResult`** JSON object (stable contract for tooling):

| Field | Meaning |
|-------|---------|
| `canonical_bundle_digest_verified` | Manifest digest recomputed from canonical rules |
| `signature_verified` | At least one valid Ed25519 signature on export signing payload |
| `schema_version_supported` | Bundle + export schema versions recognized |
| `manifest_complete` | Required manifest file entries present |
| `all_manifest_hashes_match` | On-disk file SHA-256 matches manifest |
| `all_evidence_references_resolve` | Evidence and finding reference paths exist in zip |
| `replay_validation_passed` | Deterministic governance replay succeeded |
| `unsigned_dependency_detected` | Required unsigned attachment declared but missing |
| `overall_status` | Primary outcome category (see below) |
| `failures` | Array of `{stage, code, message}` with per-stage detail |

Optional context: `run_id`, `export_schema_version`, `bundle_schema_version`, `signature_issuer_id`, `replay_ok`.

### `overall_status` values

| Value | Typical cause |
|-------|----------------|
| `success` | All stages passed |
| `signature_invalid` | Missing, wrong key, or digest mismatch on signature |
| `bundle_tampered` | Canonical manifest digest mismatch |
| `missing_evidence` | Missing file, ref, or required unsigned attachment |
| `unsupported_schema_version` | Unknown bundle or export schema |
| `hash_mismatch` | File or export content hash mismatch |
| `replay_validation_failure` | Chain, lifecycle, or verdict replay failed |
| `incomplete_manifest` | Manifest parse or structural completeness failure |

Inspect **boolean flags and `failures`** — do not treat `overall_status` alone as sufficient for audit reporting.

## Cryptographic validity vs export completeness

These are **independent** dimensions:

**Cryptographic validity** (`signature_verified`, export hash fields in signing payload):

- Proves an trusted issuer signed a deterministic digest of key export fields (run id, content hashes, verdict, etc.).
- Does **not** prove the zip is complete, that attachments exist, or that governance replay succeeds.

**Export completeness** (`manifest_complete`, `all_manifest_hashes_match`, `all_evidence_references_resolve`, `unsigned_dependency_detected`):

- Proves the evidence package matches its manifest and declared references.
- Does **not** prove the signature is valid or that replay agrees with the exported verdict.

**Replay validation** (`replay_validation_passed`):

- Reconstructs governance state from `evidence_events` and checks chain, lifecycle, and verdict consistency.
- Can fail even when the signature is valid (e.g. broken `log_chain` with an unchanged signing payload).

A bundle may therefore be **signed but incomplete**, **complete but unsigned**, or **signed and complete but fail replay**. Integrators should surface all stage flags to users.

## Related docs

- Implementation audit: [`docs/reports/rust-native-signed-audit-export-verification-audit.md`](reports/rust-native-signed-audit-export-verification-audit.md)
- Runtime quickstart (live export): [`docs/quickstart-runtime.md`](quickstart-runtime.md)
- Export signing (Python): `python/aigov_py/audit_export_signing.py`
