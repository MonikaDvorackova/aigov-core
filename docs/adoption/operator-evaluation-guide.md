# Operator evaluation guide

## Purpose

Help **operators and security stakeholders** evaluate GovAI **without** assuming a full procurement cycle. This guide complements **`docs/trust/trust-manifest.json`**, **`SECURITY.md`**, and **`docs/reports/threat_model.md`**.

## What to validate in a PoC

1. **Identity and tenancy** — API keys map to isolated ledgers; no cross-tenant reads via `X-GovAI-Project` alone (`docs/security/tenant-isolation.md`).
2. **Authoritative verdict** — Only **`GET /compliance-summary`** defines promotion eligibility for a `run_id`; confirm consumers do not re-derive verdicts locally.
3. **CI binding** — Decide between **`govai check`** (verdict only) and **artefact-bound verify** (`docs/github-action.md`).
4. **Export** — `GET /api/export/:run_id` meets your retention and review needs (`docs/examples/audit_export_v1.example.json`).
5. **Failure modes** — **`BLOCKED`** with empty `missing_evidence` when approval/promotion prerequisites fail — ensure runbooks cover this (`docs/troubleshooting.md`).

## Suggested timeline (1–2 days)

| Day | Activity |
|-----|----------|
| **1** | Bring up Compose kit or hosted pilot URL; run `GET /ready`, deterministic demo or manual evidence script. |
| **2** | Wire adoption kit workflow or internal equivalent; dry-run **without** production keys; review export JSON with security. |

## Evidence to collect internally

- Screenshots or logs of **VALID** and **BLOCKED** states for the same policy.
- One **export** JSON artifact for archival review.
- Conformance output from **`examples/adoption/standards-conformance-kit/`** if interchange matters to your program.

## Limitations

This guide **does not** constitute legal advice or certification readiness. **Billing**, if used, follows **`docs/billing.md`** separately.

## Related

- `docs/adoption/reference-implementations.md` · `docs/adoption/quickstart-matrix.md` · `examples/reference/enterprise-deployment/README.md`
