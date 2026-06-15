# Rust-native signed audit export verification

Offline verification for signed audit export zip bundles (`aigov.audit_export_bundle.v1`). Customers, auditors, and downstream tooling can validate cryptographic integrity and export completeness without a running GovAI instance.

## Architecture

Verification is split into independent stages with structured results:

1. **Bundle manifest** — parse `manifest.json`, verify schema, recompute canonical bundle digest.
2. **Manifest completeness** — required files present, per-file SHA-256 matches, evidence/finding references resolve.
3. **Unsigned dependencies** — required explanatory attachments declared in manifest are present.
4. **Export integrity** — `aigov.audit_export.v1` schema, run_id consistency, portable `events_content_sha256`, bundle hash field format.
5. **Signature** — Ed25519 over canonical signing payload (distinct from completeness).
6. **Replay validation** — deterministic governance replay via existing `replay_engine`.

A valid signature does **not** imply a complete or trustworthy evidence package. Callers inspect per-stage booleans and `overall_status`.

### Bundle layout

```
bundle.zip
├── manifest.json          # aigov.audit_export_bundle.v1
├── audit_export.json      # signed aigov.audit_export.v1
├── evidence/...           # optional referenced attachments
└── findings/...           # optional finding artifacts
```

Canonical bundle digest: SHA-256 over recursively key-sorted manifest JSON excluding `canonical_bundle_digest_sha256`, with `files` sorted by `path`.

Export signing payload matches Python `aigov_py.audit_export_signing` (schema_version, run_id, policy_version, environment, bundle_sha256, events_content_sha256, chain_head_record_sha256, decision_verdict).

## Verification stages

| Flag | Stage |
|------|--------|
| `schema_version_supported` | Bundle + export schema |
| `canonical_bundle_digest_verified` | Manifest digest reconstruction |
| `manifest_complete` | Required manifest entries present |
| `all_manifest_hashes_match` | File SHA-256 vs manifest |
| `all_evidence_references_resolve` | Evidence + finding refs |
| `unsigned_dependency_detected` | Required unsigned attachment missing |
| `signature_verified` | Ed25519 + issuer trust |
| `replay_validation_passed` | Replay engine + validation report |

`overall_status` values: `success`, `signature_invalid`, `bundle_tampered`, `missing_evidence`, `unsupported_schema_version`, `hash_mismatch`, `replay_validation_failure`, `incomplete_manifest`.

## Files changed

| File | Role |
|------|------|
| `rust/src/canonical_json.rs` | Shared canonical JSON + SHA-256 helpers |
| `rust/src/audit_export_signing.rs` | Export signing payload + Ed25519 verify/sign |
| `rust/src/audit_export_bundle.rs` | Bundle manifest schema + zip I/O + digest |
| `rust/src/audit_export_verification.rs` | Structured verifier + negative-path tests |
| `rust/src/bin/verify_audit_export_bundle_once.rs` | Offline CLI binary |
| `rust/Cargo.toml` | `zip` dependency, new binary |
| `rust/Cargo.lock` | Lockfile update |
| `rust/src/lib.rs` | Module exports |
| `python/aigov_py/verify_audit_export_bundle.py` | Python wrapper for Rust binary |
| `python/aigov_py/cli.py` | `govai verify-evidence-pack --bundle --json` |

## Test coverage

Rust unit tests (10 negative-path scenarios in `audit_export_verification.rs`):

1. Valid bundle
2. Valid signature + modified attachment (hash mismatch)
3. Valid signature + missing manifest file
4. Valid signature + missing evidence reference
5. Unsupported schema version
6. Broken hash chain (replay failure)
7. Reordered manifest keys (digest still verifies)
8. Changed canonical manifest content (digest failure)
9. Extra unsigned file referenced by report (missing dependency)
10. Replay validation failure while signature remains valid

Additional tests in `audit_export_signing.rs` and `audit_export_bundle.rs`.

## Validation commands

```bash
cd rust && cargo test --locked
cd python && python -m pytest -q
python scripts/gate_reports.py
make cursor-plugin-smoke
```

Offline bundle verification:

```bash
cd rust && cargo build --bin verify_audit_export_bundle_once
export AIGOV_POLICY_TRUST_ED25519_JSON='[{"issuer_id":"govai-export-signer","pubkeys_base64":["..."]}]'
govai verify-evidence-pack --bundle /path/to/bundle.zip --json
```

## Remaining risks

- Bundle pack **creation** is not yet exposed as a first-class CLI; verification assumes bundles are produced by export/signing pipelines that follow the manifest contract.
- Trust store must be configured offline (`AIGOV_POLICY_TRUST_ED25519_JSON`); no embedded trust roots.
- Replay validation uses default `PolicyConfig`; custom policy files may change replay outcomes vs export-time policy unless callers align config.
- Zip bombs / oversized archives are not size-limited in the verifier.

## Evaluation gate

- [x] Verifier separates cryptographic validity from completeness
- [x] Structured multi-stage results (not a single boolean)
- [x] Canonical bundle digest verification
- [x] Manifest completeness + hash verification
- [x] Ed25519 signature verification with issuer binding
- [x] Replay validation integrated
- [x] Negative-path test suite (10 scenarios)
- [x] CLI: `govai verify-evidence-pack --bundle --json`
- [x] Core remains Engine-independent

## Human approval gate

- [ ] Security review of bundle manifest schema and trust-store handling
- [ ] Product sign-off on `overall_status` taxonomy for auditor-facing tooling
- [ ] Confirm export pipeline publishes bundles matching `aigov.audit_export_bundle.v1`
