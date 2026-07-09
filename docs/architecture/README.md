# Enterprise architecture documentation

This directory is the **canonical architecture entry** for enterprise architects, procurement and security reviewers, platform engineering teams, and AI governance leads evaluating GovAI.

GovAI is **evidence-grade AI governance infrastructure**: append-only audit evidence, deterministic policy evaluation, and a single authoritative **compliance verdict** per run. It is not generic AI observability, a copilot wrapper, or a marketing-only compliance SaaS.

## Product split (read first)

| Product | Role | Primary documentation |
|---------|------|------------------------|
| **AIGov Core** | Portable audit runtime: ledger, policy enforcement at ingest, compliance projection, export and replay semantics | [platform-vs-core-boundary.md](platform-vs-core-boundary.md), [../strong-core-contract-note.md](../strong-core-contract-note.md), [../../ARCHITECTURE.md](../../ARCHITECTURE.md) |
| **GovAI Platform** | Proprietary hosted SaaS, enterprise control plane, billing, onboarding, dashboard, governance operations | [platform-vs-core-boundary.md](platform-vs-core-boundary.md), [../hosted-backend-deployment.md](../hosted-backend-deployment.md), [../../ENTERPRISE_LAYER.md](../../ENTERPRISE_LAYER.md) |

Repository packaging is described in [../../OPEN_SOURCE_SCOPE.md](../../OPEN_SOURCE_SCOPE.md) (stable filename; describes Platform vs Core boundaries).

## Canonical terminology

Use [../terminology.md](../terminology.md) in RFPs, architecture reviews, and internal runbooks. Avoid observability-only framing for governance verdicts and audit evidence.

## Architecture map

| Topic | Document |
|-------|----------|
| Overview and component layers | [overview.md](overview.md) |
| Platform vs Core boundary | [platform-vs-core-boundary.md](platform-vs-core-boundary.md) |
| Hosted vs self-host topology | [hosted-vs-self-host-topology.md](hosted-vs-self-host-topology.md) |
| Governance semantics (VALID / INVALID / BLOCKED) | [governance-semantics.md](governance-semantics.md) |
| Governance execution flow | [governance-execution-flow.md](governance-execution-flow.md) |
| Evidence lifecycle | [evidence-lifecycle.md](evidence-lifecycle.md) |
| Policy evaluation lifecycle | [policy-evaluation-lifecycle.md](policy-evaluation-lifecycle.md) |
| Decision trace lifecycle | [decision-trace-lifecycle.md](decision-trace-lifecycle.md) |
| Append-only ledger semantics | [append-only-ledger-semantics.md](append-only-ledger-semantics.md) |
| Tenant isolation (architecture view) | [tenant-isolation-architecture.md](tenant-isolation-architecture.md) |
| Trust model (verdicts and evidence, concise) | [../trust-model.md](../trust-model.md) |

## Diagrams

| Diagram | File |
|---------|------|
| High-level components | [diagrams/high_level_architecture.md](diagrams/high_level_architecture.md) |
| Evidence lifecycle | [diagrams/evidence_lifecycle.md](diagrams/evidence_lifecycle.md) |
| Policy engine flow | [diagrams/policy_engine_flow.md](diagrams/policy_engine_flow.md) |
| Runtime governance flow | [diagrams/runtime_governance_flow.md](diagrams/runtime_governance_flow.md) |
| Approval gate flow | [diagrams/approval_gate_flow.md](diagrams/approval_gate_flow.md) |
| Audit replay | [diagrams/audit_replay_architecture.md](diagrams/audit_replay_architecture.md) |
| Tenant isolation model | [diagrams/tenant_isolation_model.md](diagrams/tenant_isolation_model.md) |
| CI/CD compliance flow | [diagrams/ci_cd_compliance_flow.md](diagrams/ci_cd_compliance_flow.md) |

## Related enterprise material

| Audience | Start here |
|----------|------------|
| Security and trust | [../trust/enterprise-trust-package.md](../trust/enterprise-trust-package.md), [../security/security-overview.md](../security/security-overview.md) |
| Shared responsibility (hosted and self-host) | [../trust/shared-responsibility-model.md](../trust/shared-responsibility-model.md) |
| EU AI Act (indicative mapping, non-certifying) | [../regulatory/ai-act-mapping.md](../regulatory/ai-act-mapping.md), [../regulatory/ai-act-enterprise-positioning.md](../regulatory/ai-act-enterprise-positioning.md) |
| Developer onboarding flow | [developer_onboarding_flow.md](developer_onboarding_flow.md) |
