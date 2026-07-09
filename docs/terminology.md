# Canonical terminology

Use these terms consistently in architecture reviews, RFPs, security questionnaires, and internal runbooks. Avoid drift into observability-only or startup marketing language.

## Products and packaging

| Term | Definition | Do not confuse with |
|------|------------|---------------------|
| **AIGov Core** | Portable audit runtime: ledger, policy at ingest, compliance verdict, export/replay | “Open core” as a vague label; generic logging |
| **GovAI Platform** | Proprietary hosted SaaS, billing, onboarding, dashboard, enterprise control plane | AIGov Core alone |
| **Hosted Professional** | Self-service hosted Platform tier with Stripe checkout and operator-managed runtime | Enterprise self-host |
| **Enterprise** | Contracted tier: advanced control plane, isolation, and operational expectations per order form | Legal “enterprise” as certification |
| **Strategic Advisory** | Advisory engagement tier (process and architecture guidance); not a separate runtime | Product license |

## Governance execution

| Term | Definition |
|------|------------|
| **Governance execution** | End-to-end path from evidence ingest through policy evaluation to authoritative compliance verdict |
| **Policy evaluation** | Schema + `policy.rs` at ingest; projection rules when building summary |
| **Governance state** | Derived `ComplianceCurrentState` and verdict for a `run_id` |
| **Workflow state** | Platform `compliance_workflow` queue; operational overlay only |

## Evidence and decisions

| Term | Definition |
|------|------------|
| **Audit evidence** | Typed events accepted via `POST /evidence` into the append-only ledger |
| **Compliance verdict** | `VALID`, `INVALID`, or `BLOCKED` from `GET /compliance-summary` |
| **Decision trace** | Portable multi-step trace artefact (`governance_decision_trace`); bind via evidence for ledger authority |
| **Evidence replay** | Offline reproduction of verdict and digest checks from export |
| **Chain of custody** | Custody stages from submit → ledger → export → independent verify |

## Deprecated or discouraged phrasing

| Avoid | Prefer |
|-------|--------|
| “AI observability platform” (for GovAI product) | Audit-backed governance infrastructure |
| “AI copilot governance” | Governance execution + audit evidence |
| “Monitoring pass/fail” (for verdict) | Compliance verdict / governance gate |
| “AI Act compliant” (product claim) | Indicative AI Act mapping; operator conformity process |
| “Certified by GovAI” | Deterministic validators; evidence export for your assessors |

## Verdict glossary

| Verdict | One-line meaning |
|---------|------------------|
| **VALID** | Recorded evidence satisfies policy; promotion allowed when your gate requires it |
| **INVALID** | Evidence present; decisive policy rule failed |
| **BLOCKED** | Not eligible for `VALID`; missing evidence and/or unmet approval prerequisites |

Formal semantics: [architecture/governance-semantics.md](architecture/governance-semantics.md). Concise trust narrative: [trust-model.md](trust-model.md).
