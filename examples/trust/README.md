# Cryptographic trust examples

Illustrative JSON for **signed evidence packs** and **verification results** aligned with `trust/signing-profile.json` and `trust/verification-profile.json`.

These files are validated by `scripts/trust_chain_check.py` together with the canonical artefacts under `trust/`.

| File | Role |
|------|------|
| `sample-signed-evidence-pack.json` | Example `signed_evidence_pack` with digest and detached JWS placeholders. |
| `sample-verification-result.json` | Example `verification_result` for automation-friendly reporting. |

Run from the repository root:

```bash
python3 scripts/trust_chain_check.py
make trust-chain-check
```

Canonical documentation: `docs/trust/evidence-signing.md`, `docs/trust/verification-workflows.md`, and `trust/README.md`.
