# Audit Export Verifier Fixture Contract

This document defines the first fixture contract for the signed audit export
verifier discussed in issue #31.

It is contract-first on purpose. The Rust `VerificationResult` types should
reflect real fixture outcomes rather than anticipated verifier structure.

## Scope

This contract applies to signed `aigov.audit_export.v1` bundles verified by the
future Rust-native verifier.

It complements, but does not replace:

- [`signed-evidence-bundles.md`](signed-evidence-bundles.md)
- [`schemas/aigov.audit_export.v1.schema.json`](schemas/aigov.audit_export.v1.schema.json)

## Result Shape

A verifier result should keep a simple CI-friendly overall verdict while also
exposing staged, machine-readable details.

Suggested top-level stages:

```text
digest_verification
signature_verification
schema_compatibility
manifest_integrity
evidence_completeness
unsigned_dependency_check
```

Each stage should expose:

| Field | Purpose |
| --- | --- |
| `status` | `passed`, `failed`, `skipped`, or `not_applicable`. |
| `reason_code` | Stable machine-readable failure or skip reason. |
| `message` | Human-readable explanation for CLI/auditor output. |
| `fatal` | Whether this stage failure makes the whole export invalid in the current verifier mode. |

Human-readable messages may evolve, but `reason_code` values should be treated
as part of the serialized verifier contract once fixtures land.

## Initial Reason Codes

| Reason code | Stage | Condition |
| --- | --- | --- |
| `digest_mismatch` | `digest_verification` | Canonical bundle digest cannot be reconstructed to the expected value. |
| `signature_invalid` | `signature_verification` | Signature bytes do not verify against the trusted key for the issuer. |
| `trusted_key_missing` | `signature_verification` | Export references an issuer/key that is not present in configured trust material. |
| `unsupported_schema_version` | `schema_compatibility` | `schema_version` is not supported by this verifier. |
| `manifest_file_missing` | `manifest_integrity` | A manifest-declared file or logical section is absent. |
| `manifest_hash_mismatch` | `manifest_integrity` | A manifest-declared hash does not match the verified content. |
| `evidence_pointer_unresolved` | `evidence_completeness` | A finding subject or evidence pointer does not resolve inside the signed export. |
| `unsigned_dependency_required` | `unsigned_dependency_check` | The export requires an unsigned external file to explain the evidence. |

## Fixture Matrix

Each reason code should eventually have one fixture and one serialized
`VerificationResult` snapshot.

| Fixture | Expected reason code | Purpose |
| --- | --- | --- |
| `valid-signed-export/` | none | Verifies the happy path and stable serialized success result. |
| `invalid-digest-mismatch/` | `digest_mismatch` | Proves canonical digest reconstruction is enforced. |
| `invalid-signature/` | `signature_invalid` | Proves cryptographic signature failure is distinct from completeness failure. |
| `missing-trusted-key/` | `trusted_key_missing` | Proves trust material errors are not reported as generic bad signatures. |
| `unsupported-schema-version/` | `unsupported_schema_version` | Proves compatibility failures are explicit. |
| `missing-manifest-file/` | `manifest_file_missing` | Proves absent manifest-declared content is detected. |
| `manifest-hash-mismatch/` | `manifest_hash_mismatch` | Proves signed-but-mutated bundle content is detected. |
| `unresolved-evidence-pointer/` | `evidence_pointer_unresolved` | Proves signed exports still fail when evidence is incomplete. |
| `unsigned-dependency-required/` | `unsigned_dependency_required` | Proves verifier output fails when the export depends on unsigned explanatory material. |

## Serialized Output Expectations

Each fixture should include an expected output snapshot once the Rust verifier
exists. A minimal failure snapshot should make the boundary clear:

```json
{
  "overall_verdict": "failed",
  "stages": {
    "manifest_integrity": {
      "status": "failed",
      "reason_code": "manifest_hash_mismatch",
      "fatal": true,
      "message": "Manifest entry hash did not match verified content."
    }
  }
}
```

The exact JSON envelope can change before implementation, but the fixture
contract should preserve these invariants:

1. stage status is structured, not inferred from prose;
2. reason codes are stable;
3. fatality is explicit;
4. the overall verdict remains easy for CI to consume;
5. an external auditor can distinguish invalid signature, unsupported schema,
   missing evidence, and unsigned dependency cases without reading Rust code.

## Non-Claims

This fixture contract does not implement:

- Rust verifier types;
- cryptographic verification logic;
- key management;
- hosted ledger verification;
- regulatory submission semantics.

It only defines the first reviewable contract for verifier results and negative
fixtures.
