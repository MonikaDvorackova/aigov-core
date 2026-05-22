# Security overview

This document summarizes how GovAI approaches **security posture** for enterprise review. It is descriptive documentation for operators and security teams; it does not replace your own threat modeling or contractual commitments.

```docs
preset: security-controls
```

## Scope

GovAI spans an **audit HTTP service** (Rust), **Python tooling** (CLI, evidence packs, reports), **optional hosted backends**, and **CI integrations** (for example GitHub Actions). Each layer has distinct assets, trust boundaries, and configuration surfaces.

The **GovBase dashboard** (`dashboard/` Next.js app) may be deployed alongside or separately from the audit API; public `/docs` and `/help` routes render Markdown from `docs/` and do **not** widen ledger trust boundaries by themselves.

## Principles

- **Fail-closed governance:** missing evidence, missing approvals, or integrity failures surface as **`BLOCKED`** or **`INVALID`** in the authoritative compliance projection (`GET /compliance-summary`) and in matching CLI exit codes ([trust-model.md](../trust-model.md), [cli-reference.md](../cli-reference.md)).
- **Evidence integrity:** bundles and digests are first-class; tampering or mismatch is treated as a security-relevant failure mode (`GET /verify`, `GET /verify-log`, `govai verify-evidence-pack`).
- **Tenant isolation:** operational tenant boundaries for ledger-backed routes are derived from **server-side API key mapping**, not client-supplied project headers alone. See [tenant-isolation.md](tenant-isolation.md) and root [SECURITY.md](../../SECURITY.md).
- **Readiness vs liveness:** `GET /health` is liveness-only after startup; **`GET /ready`** is the operator-grade readiness probe (Postgres, migrations, ledger). Do not point load balancers only at `/health` for dependency safety ([hosted-backend-deployment.md](../hosted-backend-deployment.md)).

## Where to read next

| Topic | Document |
|--------|----------|
| Enterprise trust package (procurement entry) | [../trust/enterprise-trust-package.md](../trust/enterprise-trust-package.md) |
| Hosted vs self-host responsibilities | [../trust/shared-responsibility-model.md](../trust/shared-responsibility-model.md) |
| Architecture and verdict semantics | [../architecture/governance-semantics.md](../architecture/governance-semantics.md) |
| Data categories and retention expectations | [data-handling.md](data-handling.md) |
| Secrets and configuration | [secrets-management.md](secrets-management.md) |
| Ledger and audit trail | [audit-ledger-security.md](audit-ledger-security.md) |
| Incidents and disclosure | [incident-response.md](incident-response.md) |
| Deployment hardening | [secure-deployment-checklist.md](secure-deployment-checklist.md) |
| Buyer-facing trust narrative | [../trust/trust-center.md](../trust/trust-center.md) |

## Out of scope

This repository documentation does **not** certify legal compliance, SOC 2, ISO 27001, or FedRAMP. Use [../trust/compliance-mapping.md](../trust/compliance-mapping.md) as a **mapping aid**, not an attestation.
