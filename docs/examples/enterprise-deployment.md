# Example: Enterprise deployment patterns for GovAI

Enterprises typically need **network boundaries**, **identity**, **backup/restore**, and **procurement artefacts**. This page maps those needs to **existing GovAI docs** — it does **not** introduce new runtime behavior.

## Use cases

- **Self-hosted audit service** behind corporate ingress (Kubernetes, VM, or Compose).
- **Segregated environments** (dev / staging / prod) with separate API keys and databases.
- **Security review** packages for vendor assessment.

## Deployment starting points

| Topic | Document |
|-------|----------|
| Docker Compose quickstart (operator) | `docs/hosted-backend-deployment.md`, README |
| Environment variables and probes | `GET /ready`, `GET /status` — README troubleshooting |
| Stripe / usage (if enabled) | `docs/billing.md` |
| Data handling | `docs/security/data-handling.md` |
| Tenant isolation | `docs/security/tenant-isolation.md` |
| Secure deployment checklist | `docs/security/secure-deployment-checklist.md` |
| Trust manifest | `docs/trust/trust-manifest.json` |

## Enterprise evidence workflow (conceptual)

1. **Provision** Postgres + audit service; configure `GOVAI_API_KEYS` / `GOVAI_API_KEYS_JSON` per environment.
2. **Issue** API keys per team or workload; **never** reuse keys across unrelated tenants.
3. **Standardize** `run_id` issuance (UUID) tied to a release candidate or change ticket.
4. **Integrate** CI using the composite action or equivalent (`docs/github-action.md`).
5. **Archive** exports via `govai export-run` or `GET /api/export/:run_id` into your GRC or object store.

## Procurement pack

Point reviewers to:

- `SECURITY.md`, `GOVERNANCE.md`, `CODE_OF_CONDUCT.md`
- `docs/reports/threat_model.md`
- `docs/commercial/security-review-checklist.md`
- Phase reports under `docs/reports/` as **process** evidence of engineering discipline

## Reference folder

**`examples/reference/enterprise-deployment/README.md`** — checklist summary and links.

## Non-claims

GovAI documentation does **not** certify SOC 2, ISO, or AI Act conformity by itself. Customers map policy modules and organizational controls separately (`docs/customer-policy-modules.md`).
