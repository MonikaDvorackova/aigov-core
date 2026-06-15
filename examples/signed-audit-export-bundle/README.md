# Signed audit export bundle demo

Small **offline** fixture for `govai verify-evidence-pack --bundle`.

| File | Purpose |
|------|---------|
| `demo.valid.zip` | Valid signed bundle (`aigov.audit_export_bundle.v1`) |
| `trust-demo.json` | Demo Ed25519 **public** keys for verification |
| `expected-verification.snapshot.json` | Golden verifier output shape (regenerate with pytest) |

## Verify (no runtime)

```bash
cd rust && cargo build --bin verify_audit_export_bundle_once && cd ..
export AIGOV_POLICY_TRUST_ED25519_JSON="$(cat examples/signed-audit-export-bundle/trust-demo.json)"
govai verify-evidence-pack --bundle examples/signed-audit-export-bundle/demo.valid.zip --json
```

Expect `"overall_status": "success"`.

## Regenerate

```bash
python3 scripts/generate_signed_audit_export_bundle_demo.py
cd rust && cargo build --bin verify_audit_export_bundle_once && cd ..
export AIGOV_POLICY_TRUST_ED25519_JSON="$(cat examples/signed-audit-export-bundle/trust-demo.json)"
govai verify-evidence-pack --bundle examples/signed-audit-export-bundle/demo.valid.zip --json
python -m pytest python/tests/test_signed_audit_export_bundle_demo.py -q
```

The demo signing key uses a **fixed test seed** documented in `scripts/generate_signed_audit_export_bundle_demo.py` — not for production.

Documentation: [`docs/signed-audit-export-verifier.md`](../../docs/signed-audit-export-verifier.md).
