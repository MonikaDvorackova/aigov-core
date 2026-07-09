# Signed evidence bundles (audit export)

AIGov Core produces deterministic **`aigov.audit_export.v1`** documents from the append-only ledger (`GET /api/export/:run_id`). **Signing** is an optional post-export step: it binds a canonical digest of export fields to an Ed25519 key without changing ledger ingest, policy enforcement, or compliance projection semantics.

## What is signed

The signing preimage (`canonical_payload`) includes:

| Field | Purpose |
|-------|---------|
| `schema_version` | Reject unsupported export formats at verify time |
| `run_id` | Bind signature to a single run |
| `policy_version` | Policy context at export time |
| `environment` | Deployment tier stamp |
| `bundle_sha256` | Bundle fingerprint from export |
| `events_content_sha256` | Portable digest over `evidence_events` |
| `chain_head_record_sha256` | Ledger chain head at export |
| `decision_verdict` | Ledger-authoritative verdict at export |

The preimage **excludes** the full `evidence_events` array and the `signatures` block. Event integrity is enforced by recomputing `events_content_sha256` during verification.

## Canonical serialization

- JSON with **sorted keys**, no insignificant whitespace (`aigov_py.canonical_json.canonical_bytes`)
- Payload digest: **SHA-256 hex** over canonical bytes (signed as UTF-8 text, same pattern as `govai.policy.v1` bundles)

## Sign an export

```bash
govai export-run --run-id "$GOVAI_RUN_ID" > /tmp/export.json

govai sign-audit-export \
  --in /tmp/export.json \
  --out /tmp/export.signed.json \
  --issuer-id govai-export-signer \
  --signer compliance-officer \
  --private-key-base64 "$ED25519_PRIVATE_KEY_B64" \
  --created-at-utc "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

Or from Python:

```python
from aigov_py.audit_export_signing import sign_audit_export_ed25519

sign_audit_export_ed25519(
    "export.json",
    out_path="export.signed.json",
    issuer_id="govai-export-signer",
    signer="compliance-officer",
    private_key_base64="...",
    created_at_utc="2026-05-01T12:00:00Z",
)
```

## Verify a signed export

```bash
export AIGOV_POLICY_TRUST_ED25519_JSON='[{"issuer_id":"govai-export-signer","pubkeys_base64":["<pubkey-b64>"]}]'

govai verify-audit-export --path /tmp/export.signed.json
```

Verification checks:

1. **Schema** — `schema_version` is `aigov.audit_export.v1`
2. **run_id consistency** — `run.run_id` matches every `evidence_events[].run_id`
3. **Event content hash** — `events_content_sha256` matches `portable_evidence_digest_v1` over events
4. **Bundle hash** — `bundle_sha256` present and valid hex
5. **Signature** — Ed25519 over payload digest with a trusted public key for `issuer_id`

Tampering with an event payload, `decision.verdict`, or hash fields without re-signing fails verification.

## Trust keys

Reuse the same trust JSON shape as policy bundle signing:

```json
[
  {
    "issuer_id": "govai-export-signer",
    "pubkeys_base64": ["<base64-encoded-32-byte-ed25519-public-key>"]
  }
]
```

Set `AIGOV_POLICY_TRUST_ED25519_JSON` for `govai verify-audit-export`, or pass `--trust-json`.

## Relationship to the ledger

| Layer | Authority |
|-------|-----------|
| Append-only ledger | Source of truth for evidence order and hashes |
| Compliance summary / export | Deterministic projection from ledger |
| Ed25519 signature | Attestation that an export snapshot was approved by a key holder |

Signatures do **not** replace `GET /verify/:run_id` or hosted ledger verification. They help auditors detect tampering **after** export download.

## Implementation

- Module: `python/aigov_py/audit_export_signing.py`
- Tests: `python/tests/test_audit_export_signing.py`
- Related: [trust/evidence-signing.md](trust/evidence-signing.md), [runtime-api-contract.md](runtime-api-contract.md)
