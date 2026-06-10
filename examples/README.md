# Examples (non-production)

This directory holds **illustrative** scripts, compose snippets, and sample payloads for learning GovAI integration patterns.

- **Not production configs** — defaults are for local study only.
- **No secrets** — do not copy API keys or tokens into these files; use your own dev credentials.
- **Canonical docs** — behavior and contracts are defined in `docs/` and `api/govai-http-v1.openapi.yaml`, not duplicated here.

| Path | Purpose |
|------|---------|
| [reconstructible-agent-demo/](reconstructible-agent-demo/) | **Reconstructible agent** — full agent lifecycle demo, export replay viewer; see [docs/reconstructible-agent-demo.md](../docs/reconstructible-agent-demo.md). |
| [basic-runtime-client/](basic-runtime-client/) | **Core runtime** — curl smoke (`POST /evidence`, summary, export, verify); see [docs/quickstart-runtime.md](../docs/quickstart-runtime.md). |
| [python-runtime-client/](python-runtime-client/) | **Core runtime** — stdlib Python smoke + optional LangChain hook adapter example. |
| [runtime-governance/](runtime-governance/) | Stdlib Python runtime SDK, FastAPI/LangChain/gateway adapters, `make runtime-sdk-check`. |
| [ci/](ci/) | Downstream GitHub Actions pattern for the artefact-bound composite action. |
| [runtime-evaluate/](runtime-evaluate/) | Minimal `POST /v1/runtime/evaluate` JSON sample (see OpenAPI + runtime governance docs). |
| [evidence-pack/](evidence-pack/) | Pointers to evidence pack generation and digest flow. |
| [docker-compose-local-demo/](docker-compose-local-demo/) | Alternate compose layout for local demos. |
| [local-demo/](local-demo/) | Read-only **`/health`**, **`/ready`**, **`/status`** curl samples + expected output notes (no API keys). |
| [commercial-demo/](commercial-demo/) | Sales / pilot oriented curl flow, VALID vs BLOCKED notes, troubleshooting (see README). |
| [customer-repos/](customer-repos/) | Documentation-only patterns (GitHub Actions, RAG, LangChain-style agents, MLflow, healthcare posture). |
| [trust/](trust/) | **Cryptographic trust** — sample signed evidence pack and verification result JSON; validate with `scripts/trust_chain_check.py` and `make trust-chain-check` (see `docs/trust/immutable-trust-chain.md`, `trust/README.md`). |
| [standards/](standards/) | **Interchange samples** for the Phase 9 registry (`evidence-pack.valid.json`, `policy-module.valid.json`, `decision-trace.valid.json`) plus Phase 5 standards golden files; validate with `scripts/validate_standard_conformance.py` (see `docs/standards/conformance.md`). |
| [adoption/](adoption/) | **Runnable adoption kits** — GitHub Actions template (no secrets by default), self-hosted Compose example, AI Act–oriented interchange JSON, offline standards conformance script; see `docs/adoption/reference-implementations.md`. |
| [integrations/](integrations/) | **Developer integrations** (`examples/integrations/`) — Python/TypeScript SDK notes, OpenAI, LangChain, MLflow, OpenTelemetry; pointers to `docs/integrations/` guides. |
| [observability/](observability/) | **Runtime observability** — local runtime events, dashboard summary, incident report examples, and a **Prometheus scrape sample** (`scrape-metrics.example.sh`) for `GET /metrics`. |
| [hosted-platform/](hosted-platform/) | **Hosted platform readiness** — manifest hook, snapshot, scoring, and export shell drivers; `make hosted-platform-check`. |
| [revenue/](revenue/) | **Revenue intelligence** — commercial signals manifest, validators, `make revenue-intelligence-check`, `make customer-success-check`. |
| [hosted/](hosted/) | **Hosted SaaS** — sample tenant config and usage report JSON; canonical narrative under `docs/hosted/`; validate with `make hosted-platform-check` and `make production-readiness-check`. |
| [tenant-console/](tenant-console/) | **Tenant console** — snapshot/CRM smoke script and sample JSON for `GET /api/tenant-console/*` management APIs; operator docs under `docs/tenant-console/`. |
| [marketplace/](marketplace/) | **Marketplace** — Phase 13 extension package samples and Phase 14 **policy pack** examples; catalog at `marketplace/manifest.json`. |
| [partners/](partners/) | **Ecosystem partnerships and integration marketplace** — sample listing JSON and shell drivers for `make integration-marketplace-check` and full `partner_ecosystem_check.py`; see `docs/partners/integration-marketplace.md` and repository-root `partner-ecosystem/`. |
| [product-analytics/](product-analytics/) | **Product analytics and growth instrumentation** — sample event stream and `run-product-analytics-check.sh`; `make product-analytics-check`, `make growth-instrumentation-check`; see `docs/product-analytics/` and repository-root `product-analytics/`. |
| [partner-ecosystem/](partner-ecosystem/) | **Partner certification** — sample partner profile JSON, certification package driver, and Phase 12 `partner_ecosystem_check.py` smoke; see `docs/partners/`. |
| [multi-tenant/](multi-tenant/) | **Multi-tenant governance** — sample tenant governance snapshot and aggregated `multi_tenant_check.py` driver; `make multi-tenant-check`, `make tenant-isolation-check`. |
| [conformity/](conformity/) | **AI Act conformity automation** — sample conformity assessment snapshot and aggregated `conformity_workflow_check.py` driver; `make conformity-workflow-check`, `make regulatory-workflow-check`. |
| [research/](research/) | **Research and academic publication** — experimental plan sample, reproducibility drivers; `make research-package-check`, `make academic-publication-check`. |
| [control-plane/](control-plane/) | **Enterprise governance** JSON samples plus **autonomous governance posture** snapshot and shell drivers; validate bundle with `python3 scripts/control_plane_check.py`, `make control-plane-check`, or `make enterprise-governance-check`; posture aggregate via `make governance-posture-check`. |
| [autonomous/](autonomous/) | **Autonomous and multi-agent governance** — role models, delegation and approval boundaries, autonomy limits, intervention points; validate with `python3 scripts/autonomous_governance_check.py`, `make autonomous-governance-check`, or `make multi-agent-governance-check` (see `docs/autonomous/`). |
| [govai-functions-2/](govai-functions-2/) | **GovAI Functions 2.0** — flight-pack JSON fixture and validator wiring (`make functions-v2-check`); see `docs/govai-functions-2.md`. |
| `demo_govai.py`, `blocked_deployment.sh` | Small scripted demos (review before running). |

**Adoption feedback:** if you tried these examples in a pilot or internal integration, use **[`docs/community/adoption-feedback-intake.md`](../docs/community/adoption-feedback-intake.md)** so maintainers can track docs and ergonomics gaps.
