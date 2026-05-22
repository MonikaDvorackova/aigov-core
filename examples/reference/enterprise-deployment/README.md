# Reference: Enterprise deployment (GovAI audit service)

Use this README as a **navigation index** for security, operations, and compliance stakeholders who are evaluating or operating GovAI **inside** an enterprise boundary.

## Primary documents

| Audience | Start here |
|----------|------------|
| Operators / SRE | `docs/hosted-backend-deployment.md`, `docs/operator-runbook.md` |
| Security | `SECURITY.md`, `docs/reports/threat_model.md`, `docs/security/secure-deployment-checklist.md` |
| Tenant / data | `docs/security/tenant-isolation.md`, `docs/security/data-handling.md` |
| Procurement | `docs/commercial/security-review-checklist.md`, `docs/commercial/procurement-legal-review-checklist.md` |
| Narrative example | `docs/examples/enterprise-deployment.md` |

## Typical topology

- **Postgres** (managed or self-hosted) + **GovAI audit API** behind corporate ingress.
- **Per-environment** keys and databases; **no** key sharing across unrelated business units.
- **CI** in GitHub Enterprise or other systems calling the same **`GET /compliance-summary`** contract.

## What enterprises should validate

- **Backup and restore** for Postgres; RPO/RTO per your policy.
- **Secrets** rotation for API keys; see `docs/security/secrets-management.md` if applicable.
- **Network** egress/ingress rules for webhooks if Stripe billing is enabled (`docs/billing.md`).

## Non-goals

This reference does **not** replace **customer-specific** threat modeling, legal interpretation, or pen tests.
