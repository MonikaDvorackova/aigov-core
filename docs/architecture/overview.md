# GovAI Architecture Overview

GovAI is an evidence-first governance layer for AI systems.

```docs
preset: architecture-components
```

The platform focuses on:
- decision-level auditability
- fail-closed enforcement
- evidence continuity
- operational governance enforcement

## High-level architecture

GovAI consists of several major layers:

1. Governance clients
2. CI/CD integrations
3. Runtime governance APIs
4. Audit ledger and evidence storage
5. Policy evaluation and enforcement
6. Evidence export and replay

```flow
preset: runtime
```

## Core concepts

### Decision-centric enforcement

GovAI evaluates whether a system decision is governable and auditable.

The system does not only evaluate model quality. It evaluates whether:
- required evidence exists
- evaluations completed
- approvals are present
- traceability is intact
- integrity guarantees hold

### Fail-closed semantics

GovAI uses three primary verdicts:

- VALID
- INVALID
- BLOCKED

Missing governance evidence produces BLOCKED rather than implicit success.

### Evidence continuity

Audit records must remain linked to exported artifacts through deterministic or cryptographic integrity mechanisms.

## Main components

## Python SDK

The Python SDK provides:
- CLI workflows
- evidence export
- replay tooling
- CI integration helpers
- compliance verification tooling

## Rust audit service

The Rust service provides:
- governance APIs
- audit ingestion
- runtime evaluation
- evidence verification
- tenant isolation
- readiness and operational endpoints

## Policy engine

The policy layer evaluates:
- governance requirements
- enforcement rules
- approval requirements
- runtime governance constraints

## CI/CD integration layer

GovAI integrates into CI/CD pipelines using:
- GitHub Actions
- evidence bundle verification
- compliance gates
- replay validation

## Runtime governance

Runtime governance allows operational enforcement after deployment.

Examples:
- runtime blocking
- approval validation
- policy checks
- evidence validation
- runtime traceability

## Tenant isolation

Tenant isolation is derived from server-side API key mapping.

Headers are metadata only and are not security boundaries.

## Deployment model

Typical deployments include:
- local development
- self-hosted audit services
- hosted governance endpoints
- CI-integrated enforcement flows

## Developer onboarding (diagram)

For a single-page view from **clone** through **runtime evaluate**, **evidence packs**, **CI gates**, and **hosted** audit URLs, see **[developer_onboarding_flow.md](developer_onboarding_flow.md)**.

## HTTP surface (where to read more)

The Rust binary exposes **core metadata** (`GET /health`, `GET /status`, …), **readiness** (`GET /ready`), and **gated ledger routes** (`POST /evidence`, `GET /compliance-summary`, `GET /bundle-hash`, `GET /api/export/:run_id`, billing, usage, …). A concise table lives in [ARCHITECTURE.md](../../ARCHITECTURE.md); normative schemas and stability tags are in [`api/govai-http-v1.openapi.yaml`](../../api/govai-http-v1.openapi.yaml). A reader summary is in [api-reference.md](../api-reference.md).

**Dashboard and enterprise APIs** (Supabase JWT, assessments, compliance workflow queues) share the same deployment in many setups but use **different auth** from audit API keys—see ARCHITECTURE and OpenAPI `Enterprise` tags.

## Shipped vs planned (high level)

| Status | Area | Notes |
|--------|------|--------|
| **Shipped** | Evidence → append-only log → bundle / compliance-summary / export | Core enforcement path in `rust/`. |
| **Shipped** | `govai` CLI + GitHub composite action | `python/aigov_py/cli.py`, root `action.yml`. |
| **Preview** | `POST /v1/runtime/evaluate` | Documented as internal/preview; does not redefine summary verdicts. |
| **Planned / roadmap** | Broader governance control plane, immutability options, multi-region DR | See [roadmap.md](../roadmap.md)—no commitment to dates in this architecture page. |

## Future directions

See [roadmap.md](../roadmap.md) for the public roadmap. Architecture themes called out there include deeper runtime governance, evidence UX, and standards/interoperability—without diluting fail-closed semantics.
