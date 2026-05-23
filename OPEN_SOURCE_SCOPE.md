# GovAI Platform vs GovAI Core (repository boundary)

**Filename note:** `OPEN_SOURCE_SCOPE.md` is kept for stable links. This document describes **what belongs in the proprietary GovAI Platform repository** versus the **GovAI Core** portable runtime maintained in **[govai-core](https://github.com/govbase-dev/govai-core)**.

Canonical terminology: [docs/terminology.md](docs/terminology.md). Architecture boundary: [docs/architecture/platform-vs-core-boundary.md](docs/architecture/platform-vs-core-boundary.md).

## License

- **This repository:** proprietary — see [LICENSE](LICENSE). No permission to use, copy, modify, distribute, host, resell, or white-label except under a written agreement with the copyright holder.
- **govai-core:** public open-core runtime under the license published in that repository (permissive open-source license for the portable audit engine and integrator surfaces).

## What lives in this repository (proprietary platform)

| Area | Examples in tree |
|------|------------------|
| Hosted SaaS | `hosted/`, `docs/hosted/`, production topology, billing readiness |
| Billing & metering | Stripe webhooks, usage plans, `docs/billing.md` |
| Onboarding & tenant lifecycle | Dashboard `/onboarding`, tenant console, API key provisioning flows |
| Enterprise control plane | `control-plane/`, JWT `/api/*`, team scope, compliance workflow |
| Dashboard & public site | `dashboard/` (govbase.dev) |
| Operational tooling | Makefile gates, CI workflows, diagnostics for platform operations |
| Commercial & launch ops | `docs/commercial/`, `docs/pricing/`, revenue and customer-success manifests |

## What lives in govai-core (public runtime)

Portable surfaces intended for redistribution and self-host without platform SaaS:

- Rust audit service (`aigov_audit`) and canonical HTTP contracts
- Python CLI / `aigov-py` and TypeScript SDK packages as published from open core
- Policy framework, standards validators, GitHub Action, and offline conformance tooling
- Documentation and examples for integrators who do not need the proprietary platform

## Semantic layers (still useful inside the platform repo)

When reading code here, distinguish:

1. **Runtime contracts** — regulation-agnostic ledger and `GET /compliance-summary` semantics (implemented in tree; canonical open-core copy migrates to **govai-core**).
2. **Demo / prototype** — Iris sklearn path, `prototype_domain` IDs (replace in production).
3. **Enterprise layer** — optional Postgres + JWT product APIs; not a substitute for ledger policy. See [ENTERPRISE_LAYER.md](ENTERPRISE_LAYER.md).

## Integrator surfaces

| Surface | Where to obtain | License context |
|---------|-----------------|-----------------|
| **Python (`aigov-py`)** | PyPI from **govai-core** release process | Open-core license in **govai-core** |
| **TypeScript SDK** | npm from **govai-core** when published | Open-core license in **govai-core** |
| **Platform dashboard & hosted APIs** | This repository / govbase.dev | Proprietary platform |
| **HTTP / OpenAPI** | Contract may be shared; hosted operation is proprietary | See order form |

Historical audit: [docs/reports/public-sdk-packages-audit.md](docs/reports/public-sdk-packages-audit.md). Boundary change audit: [docs/reports/platform-license-and-repo-boundary.md](docs/reports/platform-license-and-repo-boundary.md).

## Out of scope (unchanged product claims)

- No legal or regulatory certification from software alone.
- No promise that documentation in this repo satisfies EU AI Act or other obligations without your organization's process.
