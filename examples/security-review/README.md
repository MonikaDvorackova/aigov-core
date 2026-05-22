# Security review example

This folder supports **enterprise security reviews** of the GovAI repository: a frozen **sample JSON** shape and a **non-networking shell driver** that runs the same diagnostics CI uses for Phase 8.

## What gets exercised

| Probe | Command |
|-------|---------|
| Structured security and trust diagnostics | `python3 scripts/security_trust_check.py --json` |
| Trust manifest validation | `python3 scripts/validate_trust_manifest.py --json` |

Both scripts are **stdlib-only**, read the working tree, and emit **deterministic JSON** (sorted object keys) on stdout when passed `--json`.

## Run

From the **repository root**:

```bash
bash examples/security-review/run-security-review-check.sh
```

Expected: the script exits **0** and prints a short success line. On failure, stderr from the underlying Python commands surfaces first.

## Sample artefact

See **`sample-security-review.json`** for an illustrative document (not live output). For machine consumption in CI, use the **`security-trust.json`** and **`trust-manifest-validation.json`** files produced by **`.github/workflows/oss-developer-experience.yml`**.

## Related documentation

- **`docs/security/security-overview.md`**
- **`docs/trust/trust-center.md`**
- **`docs/trust/trust-manifest.json`**
