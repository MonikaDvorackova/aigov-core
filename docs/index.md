# GovAI documentation

Canonical Markdown for GovAI — an **audit-backed governance and compliance platform** for AI systems. Interactive reader: [govbase.dev/docs](https://govbase.dev/docs). Help center: [govbase.dev/help](https://govbase.dev/help).

On [govbase.dev/docs](https://govbase.dev/docs), the hub renders **try consoles**, **flow animations**, **searchable catalogs**, and **guided checklists** — not static Markdown walls alone.

## Start here (by role)

| Role | Start here |
|------|------------|
| **New visitor** | [product/what-is-govai.md](product/what-is-govai.md) → [product/how-govai-works.md](product/how-govai-works.md) |
| **AI engineer** | [quickstart-runtime.md](quickstart-runtime.md), [quickstart-5min.md](quickstart-5min.md), [product/integration-patterns.md](product/integration-patterns.md), [github-action.md](github-action.md) |
| **Platform / CTO** | [architecture/README.md](architecture/README.md), [architecture/overview.md](architecture/overview.md), [architecture/platform-vs-core-boundary.md](architecture/platform-vs-core-boundary.md) |
| **Compliance / legal** | [trust-model.md](trust-model.md), [regulatory/ai-act-enterprise-positioning.md](regulatory/ai-act-enterprise-positioning.md), [trust/trust-center.md](trust/trust-center.md) |
| **Enterprise buyer** | [trust/enterprise-trust-package.md](trust/enterprise-trust-package.md), [pricing/index.md](pricing/index.md), [buyer/README.md](buyer/README.md), [terminology.md](terminology.md) |
| **Contributor** | [project/local_development.md](project/local_development.md), [project/contributor_workflow.md](project/contributor_workflow.md) |

Full product index: [product/README.md](product/README.md).

## Documentation pillars

1. **Product** — `docs/product/` (overview, use cases, ROI, positioning)
2. **Developers** — quickstarts, integrations, runtime SDK, GitHub Action
3. **Architecture** — `docs/architecture/` (enterprise hub: [architecture/README.md](architecture/README.md)), [../ARCHITECTURE.md](../ARCHITECTURE.md)
4. **Enterprise governance & trust** — [terminology.md](terminology.md), [architecture/governance-semantics.md](architecture/governance-semantics.md), [trust/enterprise-trust-package.md](trust/enterprise-trust-package.md), [trust/shared-responsibility-model.md](trust/shared-responsibility-model.md)
5. **Compliance** — regulatory, conformity, trust, evidence standards
6. **Enterprise** — commercial, hosted, pilots, buyer due diligence (`docs/buyer/`)
7. **Reference** — [api-reference.md](api-reference.md), [cli-reference.md](cli-reference.md), OpenAPI
8. **Operations** — deployment, security, runbooks

## Overview

GovAI records lifecycle events as structured evidence and returns a single authoritative decision per run:

- `VALID`
- `INVALID`
- `BLOCKED`

## Product scope

GovAI:

- accepts evidence via `POST /evidence`
- returns a deterministic compliance decision via `GET /compliance-summary`
- supports CI gating by failing unless verdict is `VALID`
- exports machine-readable audit evidence via `GET /api/export/:run_id`
- supports optional hosted Stripe billing (operator-configured): Checkout, signed `POST /stripe/webhook` processing, `GET /billing/status`, Customer Portal session, invoice listing, usage reporting to Stripe, reconciliation data, and optional subscription enforcement via `GOVAI_BILLING_ENFORCEMENT` — see [billing.md](billing.md)

GovAI does not generate missing evidence and is not a legal certification.

## Stabilization readiness

Bounded operational artefacts for buyers and operators. These materials support product evaluation and operational review, but they are not a legal certification.

- Evidence map (runtime vs validators): [`product/evidence-map.md`](product/evidence-map.md), [`product/evidence-map.json`](product/evidence-map.json), validated by **`python3 scripts/evidence_map_check.py`** (**`make evidence-map-check`**).
- Security program baseline (process + index): [`security/threat-model-index.md`](security/threat-model-index.md), [`security/security-overview.md`](security/security-overview.md), and related checklist pages in **`docs/security/`**. See the threat model index for linked materials. Validated by **`python3 scripts/security_program_check.py`** (**`make security-program-check`**).
- Aggregate check: **`make stabilization-readiness-check`**. This is also included in **`make enterprise-readiness-check`**.

The public dashboard landing at **`/`** summarizes **How GovAI Works**: capture, govern, record, decide, export, and monitor. It includes a high-level pipeline diagram and does not require Supabase for rendering.

## Decision states

- `VALID`: required evidence present and policy satisfied (deployment allowed)
- `INVALID`: evidence present but fails policy (deployment rejected)
- `BLOCKED`: not eligible for promotion yet (deployment halted)

`BLOCKED` can be caused by missing required evidence (`missing_evidence` is non-empty) and/or unmet approval or promotion prerequisites (`blocked_reasons` explains why), even when `missing_evidence: []`.

## Trust and explainability (minimal)

- Definitions and non-claims: [trust-model.md](trust-model.md)
- Teaching-friendly (ČVUT-style): [cvut-teaching.md](cvut-teaching.md)
- Cryptographic signing, verification, and immutable trust-chain guidance: [trust/immutable-trust-chain.md](trust/immutable-trust-chain.md) (aggregate check: `make trust-chain-check`; with report gate: `make immutable-trust-check`)
- Machine-readable signing and verification profiles: [`../trust/signing-profile.json`](../trust/signing-profile.json), [`../trust/verification-profile.json`](../trust/verification-profile.json) (see [`../trust/README.md`](../trust/README.md))

## Commercial pricing

- **Canonical pricing:** [pricing/index.md](pricing/index.md) — open source, hosted professional, enterprise, and advisory tiers ([govbase.dev/pricing](https://govbase.dev/pricing))
- Commercial overview: [commercial/pricing.md](commercial/pricing.md)
- Buyer packaging: [buyer/pricing-and-packaging.md](buyer/pricing-and-packaging.md)

## Private pilot

- Private pilot onboarding: [pilot-onboarding.md](pilot-onboarding.md)
- Customer onboarding (hosted, ~10 minutes — canonical): [customer-onboarding-10min.md](customer-onboarding-10min.md)
- Legacy quickstart (HTTP-first / older flow): [customer-quickstart.md](customer-quickstart.md)

## OSS ecosystem

- Example customer repositories (documentation-only integration patterns): [`../examples/customer-repos/README.md`](../examples/customer-repos/README.md)
- Community governance (maintainers, RFCs, releases, recognition): [`community/maintainer-guide.md`](community/maintainer-guide.md)
- Public benchmark metadata (local stdlib runner): [`../benchmarks/README.md`](../benchmarks/README.md)
- Tutorials and demo scripts: [`tutorials/README.md`](tutorials/README.md)
- Cursor Marketplace publication package: [`../.cursor-plugin/publication/README.md`](../.cursor-plugin/publication/README.md)
- Aggregated validation: run `make oss-ecosystem-check` from the repository root (see [`../Makefile`](../Makefile))

## Public launch and ecosystem standardization

- Launch manifest and guides: [`launch/README.md`](launch/README.md), [`launch/public-launch-manifest.json`](launch/public-launch-manifest.json)
- Example snapshot and shell drivers: [`../examples/launch/README.md`](../examples/launch/README.md)
- Aggregated validation: `make public-launch-check` (public launch targets plus `make gate`)

## Research and academic publication

- Machine-readable bundle: [`../research/README.md`](../research/README.md), [`../research/research-manifest.json`](../research/research-manifest.json)
- Narrative guides: [`research/README.md`](research/README.md), [`research/benchmark-methodology.md`](research/benchmark-methodology.md), [`research/reproducibility.md`](research/reproducibility.md)
- Example plan and driver: [`../examples/research/README.md`](../examples/research/README.md)
- Validators: `python3 scripts/validate_research_manifest.py`, `python3 scripts/research_package_check.py`
- Aggregated checks: `make research-package-check`, `make academic-publication-check` (includes `make gate`)

## Research support and operational evidence

- Quantitative feasibility and synthetic microbenchmarks: [`research/quantitative-feasibility.md`](research/quantitative-feasibility.md), [`research/microbenchmarks.md`](research/microbenchmarks.md), [`research/research-support-manifest.json`](research/research-support-manifest.json)
- Empirical benchmarking and load-testing (measured hot paths, JSON artefacts): [`research/empirical-evaluation.md`](research/empirical-evaluation.md), [`research/benchmark-manifest.json`](research/benchmark-manifest.json), [`reports/tenant_console_product_ops_package.md`](reports/tenant_console_product_ops_package.md), targets `make empirical-evaluation-run`, `make manuscript-empirical-evidence-check`
- Security threat matrix and summary: [`security/threat-matrix.md`](security/threat-matrix.md), [`security/threat-model-summary.md`](security/threat-model-summary.md), sample JSON under [`../examples/security/README.md`](../examples/security/README.md)
- Legal evidentiary positioning: [`legal/evidentiary-positioning.md`](legal/evidentiary-positioning.md) (plus chain-of-custody and jurisdictional notes in the same directory)
- Privacy architecture: [`privacy/privacy-architecture.md`](privacy/privacy-architecture.md)
- Provider cooperation roadmap: [`standards/provider-cooperation-roadmap.md`](standards/provider-cooperation-roadmap.md)
- Scalability and retention: [`operations/scalability-and-retention-patterns.md`](operations/scalability-and-retention-patterns.md)
- Validators: `make manuscript-evidence-check`, `python3 scripts/research_support_check.py --json`
- Audit report: [`reports/tenant_console_product_ops_package.md`](reports/tenant_console_product_ops_package.md)

## Commercial platform readiness

- Enterprise onboarding: [commercial/enterprise-onboarding.md](commercial/enterprise-onboarding.md)
- Hosted deployment readiness (env vars, `/ready` vs `/health`, Railway, ledger, migrations): [commercial/hosted-deployment-readiness.md](commercial/hosted-deployment-readiness.md)
- **Tenant console (management APIs + dashboard):** [tenant-console/overview.md](tenant-console/overview.md) (`GET /api/tenant-console/snapshot` **v1** contract), examples: [`../examples/tenant-console/README.md`](../examples/tenant-console/README.md)
- **GovAI Functions 2.0 (decision intelligence read APIs + flight recorder extensions):** [govai-functions-2.md](govai-functions-2.md), examples: [`../examples/govai-functions-2/README.md`](../examples/govai-functions-2/README.md), TypeScript client: [`../typescript-sdk/README.md`](../typescript-sdk/README.md)
- Commercial demo (curl flows, verdict shapes): [`../examples/commercial-demo/README.md`](../examples/commercial-demo/README.md)

Pilot packaging and limits are still often agreed with the operator; self-serve product signup is not the full story yet. Where Stripe is enabled, billing automation follows [billing.md](billing.md) (Checkout, webhooks, usage reporting, optional enforcement).

## Enterprise pilot and sales package

- Pilot playbooks and templates: [`pilots/enterprise-pilot-playbook.md`](pilots/enterprise-pilot-playbook.md) (index: [`pilots/pilot-manifest.json`](pilots/pilot-manifest.json))
- Sales collateral (discovery, qualification, value narrative, demo, PoV, stakeholders): [`sales/discovery-call-guide.md`](sales/discovery-call-guide.md)
- Example driver (stdlib, no network): [`../examples/pilot-execution/README.md`](../examples/pilot-execution/README.md)
- Aggregated validation: `make pilot-check` (`pilot-execution` + `pilot-manifest` + `gate`)

## Enterprise deployment and customer operations

- Machine-readable index: [`operations/customer-operations-manifest.json`](operations/customer-operations-manifest.json)
- Runbooks and playbooks (onboarding, deployment, support, incidents, customer success, SLO/SLA, renewal, environment): [`operations/production-onboarding.md`](operations/production-onboarding.md) and the index at [`operations/README.md`](operations/README.md)
- Example driver: [`../examples/customer-operations/README.md`](../examples/customer-operations/README.md)
- Aggregated validation: `make customer-operations-check` (`customer-operations` + `customer-operations-manifest` + `production-readiness-checklist` + `gate`)

## Partner ecosystem, certification, and integration marketplace

- Machine-readable program manifest: [`partners/partner-ecosystem-manifest.json`](partners/partner-ecosystem-manifest.json)
- Ecosystem and marketplace bundle (repository root): [`../partner-ecosystem/ecosystem-manifest.json`](../partner-ecosystem/ecosystem-manifest.json), [`../partner-ecosystem/partner-segments.json`](../partner-ecosystem/partner-segments.json), [`../partner-ecosystem/integration-marketplace-catalog.json`](../partner-ecosystem/integration-marketplace-catalog.json)
- Partner and certification documentation: [`partners/README.md`](partners/README.md)
- Example drivers: [`../examples/partner-ecosystem/README.md`](../examples/partner-ecosystem/README.md), [`../examples/partners/README.md`](../examples/partners/README.md)
- Aggregated validation: `make partner-ecosystem-check` (`partner-ecosystem` + `partner-ecosystem-manifest` + `partner-certification-package` + `gate`); focused marketplace pass: `make integration-marketplace-check`
- Mintlify site: partners group links to [`../docs-site/partners/overview.mdx`](../docs-site/partners/overview.mdx) (published navigation in [`../docs-site/docs.json`](../docs-site/docs.json))

## Product analytics and growth instrumentation

- Machine-readable bundle (repository root): [`../product-analytics/product-analytics-manifest.json`](../product-analytics/product-analytics-manifest.json), [`../product-analytics/event-taxonomy.json`](../product-analytics/event-taxonomy.json), [`../product-analytics/funnel-definitions.json`](../product-analytics/funnel-definitions.json), [`../product-analytics/growth-metrics.json`](../product-analytics/growth-metrics.json), [`../product-analytics/privacy-controls.json`](../product-analytics/privacy-controls.json), [`../product-analytics/retention-metrics.json`](../product-analytics/retention-metrics.json)
- Operator documentation: [`product-analytics/README.md`](product-analytics/README.md)
- Next.js dashboard instrumentation: [`../dashboard/app/layout.tsx`](../dashboard/app/layout.tsx) (`@vercel/analytics`, `@vercel/speed-insights`)
- Example driver: [`../examples/product-analytics/README.md`](../examples/product-analytics/README.md)
- Aggregated validation: `make product-analytics-check`; with audit report gate: `make growth-instrumentation-check`
- Mintlify site: [`../docs-site/docs.json`](../docs-site/docs.json) product analytics group

## Regulatory evidence and EU AI Act mapping

- Machine-readable index: [`regulatory/regulatory-evidence-manifest.json`](regulatory/regulatory-evidence-manifest.json) (validated by `scripts/validate_regulatory_evidence_manifest.py`)
- AI Act obligations index: [`regulatory/ai-act-obligations.json`](regulatory/ai-act-obligations.json) (validated by `scripts/validate_ai_act_obligations.py`)
- Operator documentation: [`regulatory/README.md`](regulatory/README.md)
- Example driver: [`../examples/regulatory-evidence/README.md`](../examples/regulatory-evidence/README.md)
- Aggregated validation: `make regulatory-check` (`regulatory-evidence` + `regulatory-manifest` + `ai-act-obligations` + `regulatory-export` + `gate`)

## AI Act conformity automation and regulatory workflows

- Machine-readable bundle: [`../conformity/regulatory-workflow-manifest.json`](../conformity/regulatory-workflow-manifest.json) (index), [`../conformity/conformity-assessment-workflow.json`](../conformity/conformity-assessment-workflow.json), [`../conformity/ai-act-control-mapping.json`](../conformity/ai-act-control-mapping.json), [`../conformity/technical-documentation-workflow.json`](../conformity/technical-documentation-workflow.json), [`../conformity/risk-management-workflow.json`](../conformity/risk-management-workflow.json), [`../conformity/post-market-monitoring-workflow.json`](../conformity/post-market-monitoring-workflow.json), [`../conformity/incident-reporting-workflow.json`](../conformity/incident-reporting-workflow.json)
- Operator documentation: [`conformity/README.md`](conformity/README.md)
- Example driver: [`../examples/conformity/README.md`](../examples/conformity/README.md)
- Aggregated validation: `make conformity-workflow-check` (`conformity_workflow_check.py` + `gate`); focused regulatory pass: `make regulatory-workflow-check`
- Audit report: [`reports/repo-debt-audit-and-cleanup.md`](reports/repo-debt-audit-and-cleanup.md)

## Runtime observability and operational intelligence

- Runtime telemetry contract: [`observability/runtime-telemetry-contract.md`](observability/runtime-telemetry-contract.md)
- Runtime event schema and dashboard fixtures: [`../observability/runtime-event-schema.json`](../observability/runtime-event-schema.json), [`../observability/dashboard-metrics.json`](../observability/dashboard-metrics.json), and [`../observability/incident-taxonomy.json`](../observability/incident-taxonomy.json)
- Machine-readable index: [`observability/observability-manifest.json`](observability/observability-manifest.json) (validated by `scripts/validate_observability_manifest.py`)
- Sample operational snapshot: [`../examples/observability/sample-operational-snapshot.json`](../examples/observability/sample-operational-snapshot.json) (validated by `scripts/validate_operational_snapshot.py`)
- Operator documentation: [`observability/README.md`](observability/README.md)
- Example driver: [`../examples/observability/README.md`](../examples/observability/README.md)
- Aggregated validation: `make observability-check` (`observability` + `observability-manifest` + `operational-snapshot` + `operational-health-score` + `operational-intelligence-report` + `gate`)

## Runtime safety, guardrails, and human oversight

- Machine-readable index: [`runtime-safety/runtime-safety-manifest.json`](runtime-safety/runtime-safety-manifest.json) (validated by `scripts/validate_runtime_safety_manifest.py`)
- Sample snapshot: [`../examples/runtime-safety/sample-runtime-safety-snapshot.json`](../examples/runtime-safety/sample-runtime-safety-snapshot.json) (validated by `scripts/validate_runtime_safety_snapshot.py`)
- Operator documentation: [`runtime-safety/README.md`](runtime-safety/README.md)
- Example driver: [`../examples/runtime-safety/README.md`](../examples/runtime-safety/README.md)
- Aggregated validation: `make runtime-safety-check` (`runtime-safety` + `runtime-safety-manifest` + `runtime-safety-snapshot` + `runtime-safety-score` + `runtime-safety-report` + `gate`)

## Agent governance, delegation, and multi-agent control

- Machine-readable index: [`agent-governance/agent-governance-manifest.json`](agent-governance/agent-governance-manifest.json) (validated by `scripts/validate_agent_governance_manifest.py`)
- Sample delegation snapshot: [`../examples/agent-governance/sample-agent-delegation-snapshot.json`](../examples/agent-governance/sample-agent-delegation-snapshot.json) (validated by `scripts/validate_agent_delegation_snapshot.py`)
- Operator documentation: [`agent-governance/README.md`](agent-governance/README.md)
- Example driver: [`../examples/agent-governance/README.md`](../examples/agent-governance/README.md)
- Aggregated validation: `make agent-governance-check` (`agent-governance` + `agent-governance-manifest` + `agent-delegation-snapshot` + `agent-governance-score` + `agent-governance-report` + `gate`)

## Autonomous and multi-agent governance

- Machine-readable bundle: [`../autonomous/autonomous-governance-manifest.json`](../autonomous/autonomous-governance-manifest.json) (role models, delegation and approval boundaries, autonomy limits, intervention points)
- Operator documentation: [`autonomous/README.md`](autonomous/README.md)
- Example coordination sample: [`../examples/autonomous/sample-multi-agent-coordination.json`](../examples/autonomous/sample-multi-agent-coordination.json)
- Example drivers: [`../examples/autonomous/README.md`](../examples/autonomous/README.md)
- Validation: `python3 scripts/autonomous_governance_check.py`, `make autonomous-governance-check`, `make multi-agent-governance-check` (each ends with `gate`)

## Hosted platform readiness (enterprise productization)

- Machine-readable index: [`hosted-platform/hosted-platform-manifest.json`](hosted-platform/hosted-platform-manifest.json) (validated by `scripts/validate_hosted_platform_manifest.py`)
- Sample hosted readiness snapshot: [`../examples/hosted-platform/sample-hosted-readiness-snapshot.json`](../examples/hosted-platform/sample-hosted-readiness-snapshot.json) (validated by `scripts/validate_hosted_readiness_snapshot.py`)
- Operator documentation: [`hosted-platform/README.md`](hosted-platform/README.md)
- Example driver: [`../examples/hosted-platform/README.md`](../examples/hosted-platform/README.md)
- Aggregated validation: `make hosted-platform-check` (`hosted-platform` + `hosted-platform-manifest` + `hosted-readiness-snapshot` + `hosted-readiness-score` + `hosted-readiness-export` + `gate`)

## Multi-tenant governance and enterprise RBAC

- Machine-readable bundle: [`../multi-tenant/governance-manifest.json`](../multi-tenant/governance-manifest.json) (index), [`../multi-tenant/tenant-isolation-model.json`](../multi-tenant/tenant-isolation-model.json), [`../multi-tenant/role-hierarchy.json`](../multi-tenant/role-hierarchy.json), [`../multi-tenant/delegated-administration.json`](../multi-tenant/delegated-administration.json), [`../multi-tenant/environment-segmentation.json`](../multi-tenant/environment-segmentation.json), [`../multi-tenant/separation-of-duties.json`](../multi-tenant/separation-of-duties.json)
- Operator documentation: [`multi-tenant/README.md`](multi-tenant/README.md)
- Example driver: [`../examples/multi-tenant/README.md`](../examples/multi-tenant/README.md)
- Aggregated validation: `make multi-tenant-check` (`multi-tenant` + `gate`); focused isolation pass: `make tenant-isolation-check`
- Audit report: [`reports/repo-debt-audit-and-cleanup.md`](reports/repo-debt-audit-and-cleanup.md)

## Hosted SaaS (self-service productization)

- Operator narrative: [`hosted/overview.md`](hosted/overview.md) (index of tenant onboarding, billing, metering, admin, topology, production readiness, operations, security)
- Machine-readable models (repository root): [`../hosted/README.md`](../hosted/README.md) — `tenant-lifecycle.json`, `subscription-plans.json`, `usage-metering-model.json`, `customer-admin-model.json`, `production-readiness-checklist.json`, `deployment-topology.json`
- Example payloads: [`../examples/hosted/README.md`](../examples/hosted/README.md)
- Validation: `python3 scripts/hosted_platform_check.py`, `make hosted-platform-check` (includes `make gate`), and `make production-readiness-check` (checklist JSON + production-readiness doc)

## Developer integrations and automation platform

- Machine-readable manifest: [`integrations/developer-integrations-manifest.json`](integrations/developer-integrations-manifest.json) (validated by `scripts/validate_developer_integrations_manifest.py`)
- Automation pack sample: [`../examples/integrations/sample-automation-pack.json`](../examples/integrations/sample-automation-pack.json) (validated by `scripts/validate_automation_pack.py`; summary via `scripts/generate_automation_pack_summary.py`)
- Documentation (GitHub Actions, CLI, MCP, Cursor plugin, API patterns, automation packs, authentication, local tooling, troubleshooting): [`integrations/README.md`](integrations/README.md)
- Example shell drivers: [`../examples/integrations/README.md`](../examples/integrations/README.md)
- Aggregated validation: `make developer-integrations-platform-check` (`developer-integrations` + `developer-integrations-manifest` + `automation-pack` + `automation-pack-summary` + `gate`)
## Runtime governance SDK (Python, stdlib HTTP)

- Overview: [`runtime/overview.md`](runtime/overview.md)
- Python SDK: [`runtime/python-sdk.md`](runtime/python-sdk.md)
- FastAPI, LangChain, OpenAI gateway patterns: [`runtime/fastapi-integration.md`](runtime/fastapi-integration.md), [`runtime/langchain-integration.md`](runtime/langchain-integration.md), [`runtime/openai-gateway-integration.md`](runtime/openai-gateway-integration.md)
- Policy patterns, errors, deployment: [`runtime/runtime-policy-patterns.md`](runtime/runtime-policy-patterns.md), [`runtime/error-handling.md`](runtime/error-handling.md), [`runtime/deployment-guidance.md`](runtime/deployment-guidance.md)
- Examples: [`../examples/runtime-governance/README.md`](../examples/runtime-governance/README.md)
- Layout validation: `make runtime-sdk-check`
- Aggregated validation: `make runtime-sdk-platform-check` (`runtime-sdk-check` + `gate`)

## Marketplace and developer platform

- Integration guides: [`integrations/README.md`](integrations/README.md) — start with [`integrations/integration-matrix.md`](integrations/integration-matrix.md)
- Example READMEs: [`../examples/integrations/README.md`](../examples/integrations/README.md)
- Machine-readable index: [`marketplace/marketplace-manifest.json`](marketplace/marketplace-manifest.json)
- Publisher, review, compatibility, and trust documentation: [`marketplace/README.md`](marketplace/README.md)
- Example driver: [`../examples/marketplace/README.md`](../examples/marketplace/README.md)
- Aggregated validation: `make marketplace-check` (`marketplace` + `marketplace-manifest` + `extension-package` + `marketplace-listing` + `gate`)

## Policy pack marketplace

- Catalog manifest: [`../marketplace/manifest.json`](../marketplace/manifest.json)
- Pack format, publishing, review, discovery, roadmap: [`marketplace/policy-pack-format.md`](marketplace/policy-pack-format.md) and companion pages in [`marketplace/`](marketplace/)
- Example packs: [`../examples/marketplace/README.md`](../examples/marketplace/README.md) (`eu-ai-act-basic`, `financial-services-ai`, `healthcare-ai`, `internal-model-risk`, `vendor-evaluation`, `vendor-risk`)
- Aggregated validation: `make marketplace-check`, `make policy-pack-check`, and `python3 scripts/validate_marketplace_manifest.py --json --manifest marketplace/manifest.json`

## Customer analytics and expansion intelligence

- Machine-readable index: [`analytics/customer-analytics-manifest.json`](analytics/customer-analytics-manifest.json)
- Analytics documentation: [`analytics/README.md`](analytics/README.md)
- Example driver: [`../examples/customer-analytics/README.md`](../examples/customer-analytics/README.md)
- Aggregated validation: `make customer-analytics-check` (`customer-analytics` + `customer-analytics-manifest` + `customer-health-score` + `executive-business-review` + `gate`)

## Revenue intelligence and customer success analytics

- Machine-readable index: [`../revenue/revenue-intelligence-manifest.json`](../revenue/revenue-intelligence-manifest.json) (pipeline vocabulary: [`../revenue/commercial-pipeline-signals.json`](../revenue/commercial-pipeline-signals.json), CS taxonomy: [`../revenue/customer-success-signal-taxonomy.json`](../revenue/customer-success-signal-taxonomy.json))
- Operator documentation: [`revenue/README.md`](revenue/README.md) and linked pages under [`revenue/`](revenue/)
- Example driver: [`../examples/revenue/README.md`](../examples/revenue/README.md)
- Aggregated validation: `make revenue-intelligence-check` (`revenue-intelligence` + `revenue-intelligence-manifest` + `gate`); customer success bundle: `make customer-success-check`

## Policy intelligence and governance control plane

- Machine-readable index: [`policy-intelligence/policy-intelligence-manifest.json`](policy-intelligence/policy-intelligence-manifest.json)
- Operator documentation: [`policy-intelligence/README.md`](policy-intelligence/README.md)
- Example driver: [`../examples/policy-intelligence/README.md`](../examples/policy-intelligence/README.md)
- Aggregated validation: `make policy-intelligence-check` (`policy-intelligence` + `policy-intelligence-manifest` + `governance-control-snapshot` + `policy-coverage-score` + `governance-control-report` + `gate`)

## Autonomous governance posture plane

- Machine-readable manifest: [`control-plane/control-plane-manifest.json`](control-plane/control-plane-manifest.json)
- Operator documentation: [`control-plane/README.md`](control-plane/README.md)
- Example driver: [`../examples/control-plane/README.md`](../examples/control-plane/README.md)
- Aggregate validation: `make governance-posture-check` (`control-plane` aggregate + `control-plane-manifest` + `governance-posture-snapshot` + `governance-posture-score` + `control-plane-report` + `gate`)

## Enterprise governance control plane (machine-readable)

- Canonical JSON bundle (roles, delegation, escalation, ownership, examples): [`../control-plane/README.md`](../control-plane/README.md)
- Operator narrative: [`control-plane/overview.md`](control-plane/overview.md) and linked pages under [`control-plane/`](control-plane/)
- Example payloads: [`../examples/control-plane/README.md`](../examples/control-plane/README.md)
- Validators: `python3 scripts/control_plane_check.py`, `make control-plane-check`, or `make enterprise-governance-check` (`control-plane-check` + `gate`)

## Standards registry and policy pack ecosystem

- Registry JSON catalogs and validation: [`../registry/README.md`](../registry/README.md), [`../scripts/registry_check.py`](../scripts/registry_check.py) — run `make registry-check`
- Program overview: [`registry/overview.md`](registry/overview.md)
- Certification levels: [`registry/certification-program.md`](registry/certification-program.md) and [`../registry/certification-levels.json`](../registry/certification-levels.json)
- Policy pack registry view: [`../registry/policy-pack-catalog.json`](../registry/policy-pack-catalog.json) (kept aligned with [`../marketplace/manifest.json`](../marketplace/manifest.json))
- Capability taxonomy: [`registry/capability-taxonomy.md`](registry/capability-taxonomy.md)
- Submission guidelines: [`registry/submission-guidelines.md`](registry/submission-guidelines.md) and [`community/policy-pack-submissions.md`](community/policy-pack-submissions.md)
- Maintainer operations: [`community/registry-maintainer-guide.md`](community/registry-maintainer-guide.md)
- Audit report: [`reports/repo-debt-audit-and-cleanup.md`](reports/repo-debt-audit-and-cleanup.md)

## Evidence quality, provenance, and dataset governance

- Machine-readable index: [`evidence-quality/evidence-quality-manifest.json`](evidence-quality/evidence-quality-manifest.json)
- Operator documentation: [`evidence-quality/README.md`](evidence-quality/README.md)
- Example driver: [`../examples/evidence-quality/README.md`](../examples/evidence-quality/README.md)
- Aggregated validation: `make evidence-quality-check` (`evidence-quality` + `evidence-quality-manifest` + `dataset-provenance-snapshot` + `evidence-quality-score` + `dataset-governance-report` + `gate`)

## Model risk, evaluation, and assurance

- Machine-readable index: [`model-risk/model-risk-manifest.json`](model-risk/model-risk-manifest.json) (validated by `scripts/validate_model_risk_manifest.py`)
- Sample evaluation snapshot: [`../examples/model-risk/sample-model-evaluation-snapshot.json`](../examples/model-risk/sample-model-evaluation-snapshot.json) (validated by `scripts/validate_model_evaluation_snapshot.py`)
- Operator documentation: [`model-risk/README.md`](model-risk/README.md)
- Example driver: [`../examples/model-risk/README.md`](../examples/model-risk/README.md)
- Aggregated validation: `make model-risk-assurance-check` (`model-risk` + `model-risk-manifest` + `model-evaluation-snapshot` + `model-risk-score` + `model-assurance-report` + `gate`)

## Release engineering and version governance

- Machine-readable manifest: [`releases/release-manifest.json`](releases/release-manifest.json) (validated by `scripts/validate_release_manifest.py`)
- Policies and runbooks: [`releases/versioning-policy.md`](releases/versioning-policy.md), [`releases/release-checklist.md`](releases/release-checklist.md), [`releases/release-runbook.md`](releases/release-runbook.md)
- Example drivers (shell, stdlib): [`../examples/releases/README.md`](../examples/releases/README.md)
- Makefile: `make release-manifest`, `make validate-changelog`, `make generate-release-notes`, `make release-readiness-report`, and `make release-readiness-check` (aggregate gate before tagging)

## Quickstart links

- Local 5-minute demo (audit service + end-to-end flow): [quickstart-5min.md](quickstart-5min.md)
- Contributor local setup (venv, Compose, gates, tests): [project/local_development.md](project/local_development.md)
- Developer architecture flow (clone → runtime → evidence → CI → ledger): [architecture/developer_onboarding_flow.md](architecture/developer_onboarding_flow.md)
- Legacy customer / CI quickstart: [customer-quickstart.md](customer-quickstart.md)
- GitHub Action: [github-action.md](github-action.md)

## Concepts

- Event: one recorded fact about a system action.
- Bundle: a set of events for one run (`run_id`).
- Compliance summary: the decision derived from evidence.
- Audit chain: append-only, hash-chained integrity for recorded evidence.

## API surface

- OpenAPI contract (canonical v1): [`../api/govai-http-v1.openapi.yaml`](../api/govai-http-v1.openapi.yaml)
- Endpoints used in customer flows:
  - `POST /evidence`
  - `GET /compliance-summary?run_id=...`
  - `GET /api/export/:run_id`
  - `GET /verify`

## More docs

- [billing.md](billing.md) (Stripe and hosted billing)
- [common-errors.md](common-errors.md)
- [policy-contract.md](policy-contract.md)
- [technical-documentation.md](technical-documentation.md)