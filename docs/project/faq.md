# GovAI Frequently Asked Questions

## What is GovAI?

GovAI is a decision-level AI governance platform that verifies whether deployment and governance decisions are supported by complete, verifiable, and auditable evidence.

## What problem does GovAI solve?

GovAI addresses the auditability gap: the mismatch between model-centric validation and decision-level accountability.

## Is GovAI a model evaluation tool?

No. GovAI does not replace model evaluation. It verifies whether governance and deployment decisions are supported by sufficient evidence.

## What does GovAI enforce?

GovAI enforces evidence completeness, evaluation status, approval requirements, artifact continuity, and tenant isolation.

## What happens when evidence is missing?

GovAI fails closed. Incomplete or unsupported decisions should result in BLOCKED rather than VALID.

## What are VALID, INVALID, and BLOCKED?

- VALID means all required evidence is present and checks passed.
- INVALID means evaluation failed.
- BLOCKED means required evidence, approvals, or audit context is missing.

## How does GovAI verify artifact integrity?

GovAI uses digest continuity to bind audit records to concrete artifacts.

## How is tenant isolation enforced?

Tenant identity is derived from server-owned API key mappings rather than request headers.

## Can GovAI run locally?

Yes. GovAI supports local deployments and a Docker Compose demo.

## Is a hosted service available?

Yes. GovAI supports hosted compliance gate deployments and may be offered as a managed service.

## Who is GovAI for?

GovAI is intended for AI engineers, MLOps teams, security teams, compliance teams, auditors, and researchers.

## Does GovAI guarantee legal compliance?

No. GovAI provides technical controls and evidence, but legal compliance depends on broader organizational and regulatory factors.

## How is GovAI monetized?

Potential monetization paths include hosted services, enterprise features, advisory work, and training.

## Where should new users start?

New users should read the README, run the local demo, and review the one-page overview and threat model.
