# Example: GitHub Actions integration with GovAI

This guide explains how teams **practically** wire GovAI into **GitHub Actions** for **artefact-bound** gates. Authoritative reference: **`docs/github-action.md`** and root **`action.yml`**.

## Use case

You want **protected-branch merges** to depend on:

1. Evidence submitted for a **stable** `run_id` (not `github.run_id` unless you intentionally reuse it).
2. **Digest continuity** between CI artefacts and the hosted ledger (when using `verify-evidence-pack`).
3. **`GET /compliance-summary`** returning **`VALID`**.

## Prerequisites

- `GOVAI_AUDIT_BASE_URL` — HTTPS base URL of the audit API.
- `GOVAI_API_KEY` — repository secret.
- `GOVAI_RUN_ID` — repository variable (UUID) shared across jobs that emit evidence and the gate.
- CI produces an **evidence pack layout** compatible with the composite action (see `action.yml` inputs).

## Minimal pattern

1. **Build / test job** produces artefacts and an evidence digest manifest under a known directory.
2. **GovAI gate job** uses `MonikaDvorackova/aigov-compliance-engine@v1` (or your fork pin) with:

   - `run_id: ${{ vars.GOVAI_RUN_ID }}`
   - `artifacts_path: <path to downloaded or produced artefacts>`
   - `base_url: ${{ vars.GOVAI_AUDIT_BASE_URL }}`
   - `api_key: ${{ secrets.GOVAI_API_KEY }}`

3. **Branch protection** requires the GovAI job on the target branch.

## Lighter alternative (`govai check`)

`govai check` reads **`GET /compliance-summary`** and exits non-zero unless the verdict is **`VALID`**. It does **not** bind CI file hashes to the ledger digest. Use it for **smoke** or **inner-loop** feedback; use **`verify-evidence-pack`** when you need **cryptographic** binding.

## Common pitfalls

| Pitfall | Fix |
|---------|-----|
| Mixing up `GOVAI_RUN_ID` and `github.run_id` | Document one UUID per release train; see README CI section. |
| Missing export when `require_export: true` | Ensure export endpoint reachable and run promoted per policy. |
| Different API keys across jobs | Same tenant mapping must apply to all evidence for that `run_id`. |

## Reference folder

See **`examples/reference/github-actions/README.md`** for a copy-paste oriented checklist and links.

## Related

- `docs/github-action.md` · `.github/workflows/compliance.yml` · `examples/ci/govai-check.yml`
