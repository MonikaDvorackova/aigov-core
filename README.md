# GovAI Core

GovAI Core is the **open-source**, ledger-authoritative audit runtime for reconstructible AI governance. The `aigov_audit` service appends evidence to tenant-scoped ledgers, enforces policy at ingest, derives **VALID / INVALID / BLOCKED** from ledger projection (`GET /compliance-summary`), exports `aigov.audit_export.v1`, and verifies hash chains.

**Quickstart:** [`docs/quickstart-runtime.md`](docs/quickstart-runtime.md) · **Mounted API contract:** [`docs/runtime-api-contract.md`](docs/runtime-api-contract.md) · **Repository scope:** [`OPEN_SOURCE_SCOPE.md`](OPEN_SOURCE_SCOPE.md)

## What this repository is

| In scope (GovAI Core) | Out of scope (GovAI Platform — separate product) |
|----------------------|--------------------------------------------------|
| Append-only evidence ingest (`POST /evidence`) | Hosted SaaS operations |
| Ledger integrity and `GET /verify` | Stripe / billing / pricing |
| Deterministic compliance summary | Dashboard access control |
| Audit export and portable standards validators | Commercial onboarding flows |
| Python CLI, runtime SDK, examples, GitHub Action patterns | Enterprise JWT `/api/*` control plane (not mounted on `aigov_audit`) |

License terms: [`LICENSE`](LICENSE). Contributor expectations: [`CONTRIBUTING.md`](CONTRIBUTING.md), [`GOVERNANCE.md`](GOVERNANCE.md), [`SECURITY.md`](SECURITY.md).

Historical documentation under `docs/hosted/`, `docs/billing/`, `docs/pricing/`, and `dashboard/` describes the **GovAI Platform** and is retained for reference only — it is **not** part of the core runtime surface mounted by `aigov_audit`.

## Strategy: audit engine, portable standards, interchange, and offline validation

GovAI is positioned at four complementary ideas:

1. **Audit-backed governance engine** — hosted or self-hosted service that ingests evidence, enforces policy at write time, and exposes **`GET /compliance-summary`** with **VALID / INVALID / BLOCKED** semantics (**evidence-first**, **fail-closed** where configured).
2. **Portable AI governance standards layer** — machine-readable artefacts (capability policies, delegation graphs, trace verification plans, governance evidence packs) with **deterministic validators** and **canonical digests** under `python/aigov_py/standards/` and `docs/standards/`.
3. **Standards interchange format** — partners can exchange JSON/YAML documents and digests **without** implying a hosted verdict; the same shapes can be validated offline and later bound to audit evidence when appropriate.
4. **Offline validator toolkit** — `govai standards …` and `python -m aigov_py.standards.cli` validate files locally; the evaluation harness (`python/aigov_py/standards/evaluation.py`) regression-checks `examples/standards/*.valid.json`, including registry interchange examples (`evidence-pack.valid.json`, `policy-module.valid.json`, `decision-trace.valid.json`).

**Hosted vs portable:** the **hosted audit service** (or self-hosted equivalent) proves append-only ledger behaviour, tenant isolation, and artefact-bound CI paths. **Portable standards** prove **structural** conformance and digest stability on disk — they do **not** by themselves prove ledger history or billing state.

**Non-goals:** standards validators do **not** certify legal compliance, do **not** replace hosted digest gates, and do **not** mutate ledgers or billing.

### Governance standards registry (interchange)

GovAI publishes an **explicit, versioned registry** of portable governance JSON artefacts (`governance_evidence_pack`, `governance_policy_module`, `governance_decision_trace`) with matching **JSON Schema** files under `schemas/` and deterministic validators in `python/aigov_py/standards/`. External implementers should start with `docs/standards/interchange-specification.md`, `docs/standards/registry.md`, and `docs/standards/conformance.md`.

**Conformance validation** (one JSON object on stdout with `--json`; fields include `ok`, `artifact_type`, `version`, `checks`, `failures`, `warnings`, `digest`):

```bash
python3 scripts/validate_standard_conformance.py --json examples/standards/evidence-pack.valid.json
make standards-conformance
make governance-standards-check
```

### Standards registry and policy pack ecosystem (catalogs)

The repository ships **`registry/*.json`** catalogs (standards, policy packs, benchmarks, certification levels, capabilities), **`scripts/registry_check.py`**, and **`docs/registry/`** guides for public/private registries, signing concepts, submissions, and review. Curated example packs are listed in **`marketplace/manifest.json`** with matching **`registry/policy-pack-catalog.json`** metadata. Validate with **`python3 scripts/registry_check.py`**, **`make registry-check`**, or **`make customer-analytics-check`** (registry validation plus **`make gate`**). Start with **`docs/registry/overview.md`**, **`docs/registry/certification-program.md`**, and **`docs/community/policy-pack-submissions.md`**.

## Releases

Release **versioning**, **cadence**, **compatibility**, and maintainer **runbooks** live under **`docs/releases/`**, including the machine-readable **[release manifest](docs/releases/release-manifest.json)**. The canonical history is **[CHANGELOG.md](CHANGELOG.md)**. Start with **[docs/releases/versioning-policy.md](docs/releases/versioning-policy.md)** and **[docs/releases/release-checklist.md](docs/releases/release-checklist.md)**; before tagging, run **`make release-readiness-check`**. Example drivers: **`examples/releases/README.md`**.

[![Join Discord](https://img.shields.io/badge/Discord-Join%20Community-5865F2?logo=discord&logoColor=white)](https://discord.gg/sRBSafRtE)

## Golden path (local demo, 2 min)

Minimal deterministic local example using the **existing evidence-pack format**:

- `docs/golden-path.md`
- `docs/evidence-pack.md` (generate a minimal customer-ready evidence pack)

## OSS developer tools (optional)

- **Read-only local audit probe** (requires a running service on **`127.0.0.1:8088`** by default): `make local-demo` or `make local-demo-curl` — see **`examples/local-demo/README.md`** and **`docs/project/local_development.md`**. No API keys; no evidence POST; no ledger writes.
- **Fail-closed BLOCKED demo (Python wrapper)** — same contract as **`examples/blocked_deployment.sh`**: after Compose + `python/.venv` + `GOVAI_*` are aligned, run **`make fail-closed-demo`** (runs **`scripts/run_fail_closed_demo.py`**). It checks **`GET /ready`**, runs the bash example, and prints **one deterministic JSON line** on stdout; exit **0** only when BLOCKED (exit code **3** from **`govai check`**) was confirmed inside the script.
- **`make oss-diagnostics`** ( **`python3 scripts/oss_diagnostics.py --json`** ) — one JSON line aggregating repo layout, **`repo_health_check`**, strict doc links, presence of Compose / demo scripts / Python+Rust roots, and a **generic** **`docs/reports/*.md`** drift check vs **`origin/staging`** (three-dot diff plus worktree and untracked paths; **exactly one** changed markdown report must appear — **no** hardcoded phase basenames; override base with **`GOVAI_OSS_DIAGNOSTICS_BASE_REF`** when needed). Included in **`make oss-diagnostics`** (and therefore in **`make enterprise-readiness-check`**).
- **`make stabilization-readiness-check`** — bounded checks for **stabilization readiness v1**: Rust Prometheus metrics smoke (`runtime-audit-metrics-check`), deterministic disaster-recovery script tests, **`scripts/evidence_map_check.py`**, and **`scripts/security_program_check.py`**. Aggregated into **`make enterprise-readiness-check`**.
- **Machine-readable OSS checks** (stdlib scripts; stdout is one JSON object when **`--json`** is set):
  - **`python3 scripts/repo_health_check.py --json`** — `ok`, `required_files_present`, `missing_required`, `checked_paths`, etc. (sorted keys).
  - **`python3 scripts/security_trust_check.py --json`** — structured enterprise readiness diagnostics: required security/trust docs, **`CODEOWNERS`**, Makefile targets (**`security-trust`**, **`trust-manifest`**, **`enterprise-readiness-check`**), OSS workflow wiring, **`examples/security-review/`**, plus **`ok`**, **`checks`**, **`failures`**, **`warnings`**, **`score`**, **`checked_paths`** (sorted keys).
  - **`python3 scripts/validate_trust_manifest.py --json`** — validates **`docs/trust/trust-manifest.json`** (required fields and on-disk references); deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/trust_chain_check.py --json`** — validates **`trust/*.json`** and **`examples/trust/*.json`** cryptographic trust shapes and cross references; deterministic JSON; exits non-zero on failure.
  - **`make trust-chain-check`** / **`make immutable-trust-check`** — Makefile wrappers; **`immutable-trust-check`** runs **`trust-chain-check`** then **`make gate`**.
  - **`python3 scripts/pilot_execution_check.py --json`** — pilot and sales package diagnostics: **`ok`**, **`checks`**, **`failures`**, **`warnings`**, **`score`**, **`checked_paths`** (sorted keys).
  - **`python3 scripts/customer_operations_check.py --json`** — customer operations diagnostics: **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`** (sorted keys).
  - **`python3 scripts/validate_pilot_manifest.py --json`** — validates **`docs/pilots/pilot-manifest.json`** (schema and on-disk references); deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/validate_customer_operations_manifest.py --json`** — validates **`docs/operations/customer-operations-manifest.json`**; deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/partner_ecosystem_check.py --json`** — partner ecosystem diagnostics: **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`** (sorted keys).
  - **`python3 scripts/validate_partner_ecosystem_manifest.py --json`** — validates **`docs/partners/partner-ecosystem-manifest.json`**; deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/regulatory_evidence_check.py --json`** — regulatory diagnostics: **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`** (sorted keys).
  - **`python3 scripts/validate_regulatory_evidence_manifest.py --json`** — validates **`docs/regulatory/regulatory-evidence-manifest.json`**; deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/validate_ai_act_obligations.py --json`** — validates **`docs/regulatory/ai-act-obligations.json`**; deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/generate_regulatory_evidence_export.py --manifest docs/regulatory/regulatory-evidence-manifest.json`** — deterministic Markdown export to stdout (optional **`--out`**).
  - **`python3 scripts/observability_check.py --json`** — runtime observability contract diagnostics for **`observability/runtime-event-schema.json`**, event examples, dashboard metrics, incident taxonomy, and sample JSONL: **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`** (sorted keys).
  - **`python3 scripts/validate_observability_manifest.py --json`** — validates **`docs/observability/observability-manifest.json`**; deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/validate_operational_snapshot.py --input examples/observability/sample-operational-snapshot.json --json`** — validates an operational snapshot; deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/operational_health_score.py --input examples/observability/sample-operational-snapshot.json`** — deterministic scoring with **`ok`**, **`health_score`**, **`readiness_score`**, **`evidence_score`**, **`diagnostics_score`**, **`risk_level`**, **`findings`** (sorted keys).
  - **`python3 scripts/generate_operational_intelligence_report.py --input examples/observability/sample-operational-snapshot.json`** — deterministic Markdown operational intelligence report to stdout (optional **`--out`**).
  - **`python3 scripts/runtime_safety_check.py --json`** — runtime safety diagnostics: **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`** (sorted keys).
  - **`python3 scripts/validate_runtime_safety_manifest.py --json`** — validates **`docs/runtime-safety/runtime-safety-manifest.json`**; deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/validate_runtime_safety_snapshot.py --input examples/runtime-safety/sample-runtime-safety-snapshot.json --json`** — validates a runtime safety snapshot; deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/runtime_safety_score.py --input examples/runtime-safety/sample-runtime-safety-snapshot.json`** — deterministic scoring with **`ok`**, **`runtime_safety_score`**, pillar scores, **`risk_level`**, **`findings`**, **`recommendations`** (sorted keys).
  - **`python3 scripts/generate_runtime_safety_report.py --input examples/runtime-safety/sample-runtime-safety-snapshot.json`** — deterministic Markdown runtime safety report to stdout (optional **`--out`**).
  - **`python3 scripts/hosted_platform_check.py --json`** — hosted platform diagnostics (hosted platform manifest and snapshot, plus repository-root **`hosted/`** SaaS models, **`docs/hosted/`**, and **`examples/hosted/`**): **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`** (sorted keys).
  - **`python3 scripts/validate_hosted_platform_manifest.py --json`** — validates **`docs/hosted-platform/hosted-platform-manifest.json`**; deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/validate_hosted_readiness_snapshot.py --input examples/hosted-platform/sample-hosted-readiness-snapshot.json --json`** — validates a hosted readiness snapshot; deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/hosted_readiness_score.py --input examples/hosted-platform/sample-hosted-readiness-snapshot.json`** — deterministic scoring with **`ok`**, **`hosted_readiness_score`**, **`deployment_score`**, **`tenant_onboarding_score`**, **`operations_score`**, **`support_score`**, **`risk_level`**, **`findings`**, **`recommendations`** (sorted keys).
  - **`python3 scripts/generate_hosted_readiness_export.py --input examples/hosted-platform/sample-hosted-readiness-snapshot.json`** — deterministic customer-facing Markdown to stdout (optional **`--out`**).
  - **`python3 scripts/conformity_workflow_check.py --json`** — AI Act conformity workflow diagnostics: **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`**, **`regulatory_workflow_only`**, **`version`** (sorted keys).
  - **`python3 scripts/multi_tenant_check.py --json`** — multi-tenant governance diagnostics: **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`**, **`tenant_isolation_only`**, **`version`** (sorted keys).
  - **`python3 scripts/validate_marketplace_manifest.py --json`** — validates **`docs/marketplace/marketplace-manifest.json`**; deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/validate_extension_package.py --json`** — validates a marketplace extension package JSON (sample: **`examples/marketplace/sample-extension-package.json`**); deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/marketplace_check.py --json`** — marketplace diagnostics: **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`** (sorted keys).
  - **`python3 scripts/release_operations_check.py --json`** — release operations diagnostics (required **`docs/releases/`** policy files, **`docs/releases/release-manifest.json`**, embedded manifest/changelog validators, **`CHANGELOG.md`** **Unreleased**, README/CONTRIBUTING cross-links, Makefile release targets): **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`** (sorted keys).
  - **`python3 scripts/validate_release_manifest.py --json`** — validates **`docs/releases/release-manifest.json`** (required fields + on-disk references); deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/validate_changelog.py --json`** — **Keep a Changelog** structure gate for **`CHANGELOG.md`**; deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/generate_release_notes.py --version X.Y.Z`** — deterministic Markdown release notes (optional **`--out`**); **`make generate-release-notes`** writes the sample under **`examples/releases/`**.
  - **`python3 scripts/release_readiness_report.py --json`** — aggregated readiness (**manifest** + **changelog** + **release_operations_check** + Makefile wiring); deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/validate_docs_links.py --strict --json`** — `ok`, `checked_files`, `broken_links`, `strict`, `warnings` (sorted keys).
  - **`python3 scripts/developer_integrations_check.py --json`** — developer integration docs/examples diagnostics: **`ok`**, **`failures`**, **`present`**, **`checked_paths`**, **`version`** (sorted keys).
  - **`python3 scripts/validate_marketplace_manifest.py --json`** — validates **`docs/marketplace/marketplace-manifest.json`** by default; deterministic JSON; exits non-zero on failure. Use **`marketplace/manifest.json`** for the policy pack catalog.
  - **`python3 scripts/validate_extension_package.py --json`** — validates a marketplace extension package JSON (sample: **`examples/marketplace/sample-extension-package.json`**); deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/validate_policy_pack.py --json`** — validates one policy pack directory (see **`examples/marketplace/`**); deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/registry_check.py --json`** — validates **`registry/*.json`** catalogs, cross-references, and marketplace alignment; deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/marketplace_check.py --json`** — marketplace diagnostics, including extension marketplace, policy pack marketplace assets, and registry alignment: **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`** (sorted keys).
  - **`python3 scripts/customer_analytics_check.py --json`** — customer analytics diagnostics: **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`** (sorted keys).
  - **`python3 scripts/validate_customer_analytics_manifest.py --json`** — validates **`docs/analytics/customer-analytics-manifest.json`**; deterministic JSON; exits non-zero on failure.
  - **`python3 scripts/customer_health_score.py --input examples/customer-analytics/sample-customer-health.json`** — deterministic health, adoption, risk, expansion scores and renewal signal.
  - **`python3 scripts/generate_executive_business_review.py --input examples/customer-analytics/sample-customer-health.json`** — deterministic Executive Business Review Markdown.
  - **`python3 scripts/revenue_intelligence_check.py --json`** — revenue intelligence and customer success analytics diagnostics: **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`** (sorted keys).
  - **`python3 scripts/validate_revenue_intelligence_manifest.py --json`** — validates **`revenue/revenue-intelligence-manifest.json`**; deterministic JSON; exits non-zero on failure.
- **`python3 scripts/evidence_quality_check.py --json`** — evidence quality diagnostics (manifest, snapshot validators, scoring, report wiring, Makefile **`evidence-quality-check`**, OSS workflow artefacts): **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`**, **`version`** (sorted keys).
- **`python3 scripts/validate_evidence_quality_manifest.py --json`** — validates **`docs/evidence-quality/evidence-quality-manifest.json`**; deterministic JSON; exits non-zero on failure.
- **`python3 scripts/validate_dataset_provenance_snapshot.py --json`** — validates dataset provenance snapshot JSON (sample: **`examples/evidence-quality/sample-dataset-provenance-snapshot.json`**); deterministic JSON; exits non-zero on failure.
- **`python3 scripts/evidence_quality_score.py --input examples/evidence-quality/sample-dataset-provenance-snapshot.json`** — deterministic evidence quality, provenance, lineage, and retention scores plus **`risk_level`**.
- **`python3 scripts/generate_dataset_governance_report.py --input examples/evidence-quality/sample-dataset-provenance-snapshot.json`** — deterministic dataset governance Markdown (optional **`--out`**).
- **`python3 scripts/policy_intelligence_check.py --json`** — policy intelligence diagnostics: **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`** (sorted keys).
- **`python3 scripts/validate_policy_intelligence_manifest.py --json`** — validates **`docs/policy-intelligence/policy-intelligence-manifest.json`**; deterministic JSON; exits non-zero on failure.
- **`python3 scripts/validate_governance_control_snapshot.py --json`** — validates a governance control snapshot JSON (sample: **`examples/policy-intelligence/sample-governance-control-snapshot.json`**); deterministic JSON; exits non-zero on failure.
- **`python3 scripts/policy_coverage_score.py --input examples/policy-intelligence/sample-governance-control-snapshot.json --json`** — deterministic policy coverage, control maturity, and gap risk scores with findings and recommendations.
- **`python3 scripts/generate_governance_control_report.py --input examples/policy-intelligence/sample-governance-control-snapshot.json`** — deterministic governance control Markdown report.
- **`python3 scripts/developer_integrations_check.py --json`** — developer integrations diagnostics: **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`** (sorted keys).
- **`python3 scripts/validate_developer_integrations_manifest.py --json`** — validates **`docs/integrations/developer-integrations-manifest.json`**; deterministic JSON; exits non-zero on failure.
- **`python3 scripts/validate_automation_pack.py --json --pack examples/integrations/sample-automation-pack.json`** — validates the sample automation pack schema and references.
- **`python3 scripts/generate_automation_pack_summary.py --pack examples/integrations/sample-automation-pack.json`** — deterministic Markdown summary for the sample automation pack.

The **`.github/workflows/oss-developer-experience.yml`** workflow runs **`make cursor-plugin-check`** (lightweight manifest and MCP smoke), then **`make enterprise-readiness-check`** (**`security-trust`**, **`trust-manifest`**, then **`oss-diagnostics`**), and writes **`repo-health.json`**, **`security-trust.json`**, **`trust-manifest.json`**, **`trust-manifest-validation.json`**, **`docs-links.json`**, **`oss-diagnostics.json`**, **`commercial-readiness.json`**, **`pilot-execution.json`**, **`pilot-manifest-validation.json`**, **`revenue-manifest-validation.json`**, **`revenue-roi.json`**, **`revenue-enablement.json`**, **`customer-operations.json`**, **`customer-operations-manifest-validation.json`**, **`production-readiness-checklist.md`**, **`partner-ecosystem.json`**, **`partner-ecosystem-manifest-validation.json`**, **`partner-certification-package.md`**, **`regulatory-evidence.json`**, **`regulatory-manifest-validation.json`**, **`ai-act-obligations-validation.json`**, **`regulatory-evidence-export.md`**, **`observability.json`**, **`observability-manifest-validation.json`**, **`operational-snapshot-validation.json`**, **`operational-health-score.json`**, **`operational-intelligence-report.md`**, **`runtime-safety.json`**, **`runtime-safety-manifest-validation.json`**, **`runtime-safety-snapshot-validation.json`**, **`runtime-safety-score.json`**, **`runtime-safety-report.md`**, **`hosted-platform.json`**, **`hosted-platform-manifest-validation.json`**, **`hosted-readiness-snapshot-validation.json`**, **`hosted-readiness-score.json`**, **`hosted-readiness-export.md`**, **`model-risk.json`**, **`model-risk-manifest-validation.json`**, **`model-evaluation-snapshot-validation.json`**, **`model-risk-score.json`**, **`model-assurance-report.md`**, **`agent-governance.json`**, **`agent-governance-manifest-validation.json`**, **`agent-delegation-snapshot-validation.json`**, **`agent-governance-score.json`**, **`agent-governance-report.md`**, **`autonomous-governance.json`**, **`autonomous-multi-agent-governance.json`**, **`revenue-intelligence-manifest-validation.json`**, **`revenue-intelligence.json`**, **`marketplace.json`**, **`marketplace-manifest-validation.json`**, **`policy-pack-marketplace-manifest-validation.json`**, **`registry-validation.json`**, **`policy-pack-eu-ai-act-basic-validation.json`**, **`policy-pack-financial-services-ai-validation.json`**, **`policy-pack-healthcare-ai-validation.json`**, **`policy-pack-internal-model-risk-validation.json`**, **`policy-pack-vendor-evaluation-validation.json`**, **`policy-pack-vendor-risk-validation.json`**, **`extension-package-validation.json`**, **`marketplace-listing.md`**, **`customer-analytics.json`**, **`customer-analytics-manifest-validation.json`**, **`customer-health-score.json`**, **`executive-business-review.md`**, **`evidence-quality.json`**, **`evidence-quality-manifest-validation.json`**, **`dataset-provenance-snapshot-validation.json`**, **`evidence-quality-score.json`**, **`dataset-governance-report.md`**, **`policy-intelligence.json`**, **`policy-intelligence-manifest-validation.json`**, **`governance-control-snapshot-validation.json`**, **`policy-coverage-score.json`**, **`governance-control-report.md`**, **`developer-integrations.json`**, **`developer-integrations-manifest-validation.json`**, **`automation-pack-validation.json`**, **`automation-pack-summary.md`**, **`release-manifest-validation.json`**, **`changelog-validation.json`**, **`release-readiness-report.json`**, **`release-notes-template.md`**, **`public-launch.json`**, **`public-launch-manifest-validation.json`**, **`standardization-readiness-snapshot-validation.json`**, **`public-launch-readiness-score.json`**, **`public-launch-report.md`**, **`research-package.json`**, and **`research-manifest-validation.json`** into the **`oss-check-json`** artifact.
- **Security review driver (stdlib, no network)** — **`examples/security-review/run-security-review-check.sh`** runs the same JSON probes as above; see **`examples/security-review/README.md`**.
- **Pilot execution driver (stdlib, no network)** — **`bash examples/pilot-execution/run-pilot-execution-check.sh`**; **`make pilot-execution`**, **`make pilot-manifest`**, and aggregated **`make pilot-check`** (includes **`make gate`**).
- **Customer operations driver (stdlib, no network)** — **`examples/customer-operations/`**; **`make customer-operations`**, **`make customer-operations-manifest`**, **`make production-readiness-checklist`**, and aggregated **`make customer-operations-check`** (includes **`make gate`**).
- **Partner ecosystem driver (stdlib, no network)** — **`examples/partner-ecosystem/`**; **`make partner-ecosystem`**, **`make partner-ecosystem-manifest`**, **`make partner-certification-package`**, **`make partner-ecosystem-check`** (includes **`make gate`**), and **`make integration-marketplace-check`** (integration JSON bundle plus **`make gate`**). Machine-readable ecosystem index: **`partner-ecosystem/`**; worked examples: **`examples/partners/`**.
- **Product analytics and growth instrumentation (stdlib, no network)** — **`product-analytics/`** JSON bundle, **`docs/product-analytics/`**, **`examples/product-analytics/`**; **`python3 scripts/validate_product_analytics_manifest.py`**, **`python3 scripts/product_analytics_check.py`**, **`make product-analytics-check`**, and **`make growth-instrumentation-check`** (includes **`make gate`**). Next.js **`dashboard/`** enables **`@vercel/analytics`** and **`@vercel/speed-insights`** globally in **`dashboard/app/layout.tsx`**.
- **Regulatory evidence driver (stdlib, no network)** — **`examples/regulatory-evidence/`**; **`make regulatory-evidence`**, **`make regulatory-manifest`**, **`make ai-act-obligations`**, **`make regulatory-export`**, and aggregated **`make regulatory-check`** (includes **`make gate`**).
- **Runtime observability and operational intelligence driver (stdlib, no network)** — **`examples/observability/`**; **`make observability`**, **`make observability-manifest`**, **`make operational-snapshot`**, **`make operational-health-score`**, **`make operational-intelligence-report`**, and aggregated **`make observability-check`** (includes **`make gate`**). Deterministic JSON scoring with **`ok`**, **`health_score`**, **`readiness_score`**, **`evidence_score`**, **`diagnostics_score`**, **`risk_level`**, and **`findings`** (sorted keys); deterministic Markdown intelligence report.
- **Runtime safety, guardrails, and human oversight driver (stdlib, no network)** — **`examples/runtime-safety/`**; **`make runtime-safety`**, **`make runtime-safety-manifest`**, **`make runtime-safety-snapshot`**, **`make runtime-safety-score`**, **`make runtime-safety-report`**, and aggregated **`make runtime-safety-check`** (includes **`make gate`**). Deterministic JSON with **`runtime_safety_score`**, **`guardrail_score`**, **`escalation_score`**, **`human_oversight_score`**, **`override_readiness_score`**, **`risk_level`**, **`findings`**, and **`recommendations`**; deterministic Markdown oversight report.
- **Hosted platform readiness driver (stdlib, no network)** — **`examples/hosted-platform/`**; **`make hosted-platform`**, **`make hosted-platform-manifest`**, **`make hosted-readiness-snapshot`**, **`make hosted-readiness-score`**, **`make hosted-readiness-export`**, and aggregated **`make hosted-platform-check`** (includes **`make gate`**). **`make production-readiness-check`** validates **`hosted/production-readiness-checklist.json`** and **`docs/hosted/production-readiness.md`**. Deterministic JSON scoring with **`hosted_readiness_score`**, pillar scores, **`risk_level`**, **`findings`**, and **`recommendations`**; deterministic customer-facing Markdown export. Canonical SaaS docs: **`docs/hosted/overview.md`**, machine-readable models: **`hosted/README.md`**, samples: **`examples/hosted/README.md`**.
- **GovBase hosted SaaS foundation (govbase.dev, stdlib, no network)** — **`hosted-saas/`** contracts (tenant service boundary, roles, API key scopes, billing provider boundary, monitoring, backup/DR, production topology, onboarding flow); **`python3 scripts/hosted_saas_readiness_check.py --json`**; **`make hosted-saas-readiness-check`** (includes **`hosted-platform-check`**); dashboard **`/onboarding`** checklist; audit report **`docs/reports/hosted-saas-readiness.md`**.
- **AI Act conformity automation and regulatory workflows driver (stdlib, no network)** — **`conformity/`** JSON bundle, **`docs/conformity/`**, **`examples/conformity/`**; **`python3 scripts/conformity_workflow_check.py --json`**, **`make conformity-workflow-check`** (includes **`make gate`**), and **`make regulatory-workflow-check`** (manifest plus conformity assessment workflow and AI Act control mapping focus). Cross-references AI Act obligations in **`docs/regulatory/ai-act-obligations.json`** so unknown obligation identifiers are rejected.
- **Multi-tenant governance and enterprise RBAC driver (stdlib, no network)** — **`multi-tenant/`** JSON bundle, **`docs/multi-tenant/`**, **`examples/multi-tenant/`**; **`python3 scripts/multi_tenant_check.py --json`**, **`make multi-tenant`**, **`make multi-tenant-check`** (includes **`make gate`**), and **`make tenant-isolation-check`**. OSS CI emits **`multi-tenant.json`** and **`tenant-isolation-check.json`**.
- **AI Act conformity automation and regulatory workflows driver (stdlib, no network)** — **`conformity/`** JSON bundle, **`docs/conformity/`**, **`examples/conformity/`**; **`python3 scripts/conformity_workflow_check.py --json`**, **`make conformity-workflow-check`** (includes **`make gate`**), and **`make regulatory-workflow-check`**. Cross-references AI Act obligations in **`docs/regulatory/ai-act-obligations.json`** so unknown obligation identifiers are rejected.
- **Developer integrations and automation platform driver (stdlib, no network)** — **`docs/integrations/`** guides, **`docs/integrations/developer-integrations-manifest.json`**, automation pack sample **`examples/integrations/sample-automation-pack.json`**, validators **`scripts/validate_developer_integrations_manifest.py`**, **`scripts/validate_automation_pack.py`**, **`scripts/generate_automation_pack_summary.py`**, and aggregate **`make developer-integrations-platform-check`**.
- **Runtime governance SDK (Python, stdlib HTTP)** — **`docs/runtime/`** (overview, SDK, FastAPI, LangChain, gateway, policy patterns, errors, deployment), package **`python/aigov_py/runtime/`**, examples **`examples/runtime-governance/`**, validation **`make runtime-sdk-check`**, and aggregate **`make runtime-sdk-platform-check`** (includes **`make gate`**).
- **Marketplace and developer platform driver (stdlib, no network)** — **`examples/marketplace/`**; **`make marketplace`**, **`make marketplace-check`**, **`make marketplace-manifest`**, **`make extension-package`**, and **`make marketplace-listing`**.
- **Policy pack marketplace driver (stdlib, no network)** — **`marketplace/manifest.json`**, **`examples/marketplace/*/`** packs, **`python3 scripts/validate_policy_pack.py`**, and **`make policy-pack-check`**; catalog validation via **`python3 scripts/validate_marketplace_manifest.py --manifest marketplace/manifest.json`**.
- **Customer analytics and expansion intelligence driver (stdlib, no network)** — **`docs/analytics/`** and **`examples/customer-analytics/`**; **`make customer-analytics`**, **`make customer-analytics-manifest`**, **`make customer-health-score`**, **`make executive-business-review`**, and aggregated **`make customer-analytics-check`** (includes **`make gate`**).
- **Revenue intelligence and customer success analytics driver (stdlib, no network)** — **`revenue/`** JSON, **`docs/revenue/`**, **`examples/revenue/`**; **`make revenue-intelligence`**, **`make revenue-intelligence-manifest`**, **`make revenue-intelligence-check`**, and **`make customer-success-check`** (chains the revenue intelligence aggregate including **`make gate`**).
- **Policy intelligence and governance control plane driver (stdlib, no network)** — **`docs/policy-intelligence/`** and **`examples/policy-intelligence/`**; **`make policy-intelligence`**, **`make policy-intelligence-manifest`**, **`make governance-control-snapshot`**, **`make policy-coverage-score`**, **`make governance-control-report`**, and aggregated **`make policy-intelligence-check`** (includes **`make gate`**).
- **Enterprise governance control plane (machine-readable JSON, stdlib, no network)** — repository root **`control-plane/`** (roles, delegation, escalation, ownership, examples); validate with **`python3 scripts/control_plane_check.py`**, **`make control-plane-check`**, or aggregated **`make enterprise-governance-check`** (runs **`control-plane-check`** then **`make gate`**). Operator narrative: **`docs/control-plane/overview.md`** and companion pages under **`docs/control-plane/`**; worked examples under **`examples/control-plane/`**.
- **Autonomous governance posture driver (stdlib, no network)** — **`docs/control-plane/control-plane-manifest.json`**, **`examples/control-plane/sample-governance-posture-snapshot.json`**, and narrative docs under **`docs/control-plane/`**; **`make control-plane`**, **`make control-plane-manifest`**, **`make governance-posture-snapshot`**, **`make governance-posture-score`**, **`make control-plane-report`**, and aggregated **`make control-plane-check`** (includes **`make gate`**).
- **Model risk, evaluation, and assurance driver (stdlib, no network)** — **`docs/model-risk/`**, **`examples/model-risk/`**; **`make model-risk`**, **`make model-risk-manifest`**, **`make model-evaluation-snapshot`**, **`make model-risk-score`**, **`make model-assurance-report`**, and aggregated **`make model-risk-assurance-check`** (includes **`make gate`**). Deterministic JSON with **`model_risk_score`**, pillar scores, **`assurance_level`**, **`findings`**, and **`recommendations`**; deterministic Markdown assurance report.
- **Agent governance, delegation, and multi-agent control driver (stdlib, no network)** — **`docs/agent-governance/`**, **`examples/agent-governance/`**; **`make agent-governance`**, **`make agent-governance-manifest`**, **`make agent-delegation-snapshot`**, **`make agent-governance-score`**, **`make agent-governance-report`**, and aggregated **`make agent-governance-check`** (includes **`make gate`**). Deterministic JSON with **`agent_governance_score`**, sub-scores, **`risk_level`**, **`findings`**, and **`recommendations`**; deterministic Markdown governance report.
- **Autonomous and multi-agent governance driver (stdlib, no network)** — repository root **`autonomous/`** (manifest, role models, delegation and approval boundaries, autonomy limits, intervention points), operator docs **`docs/autonomous/`**, examples **`examples/autonomous/`**; **`python3 scripts/autonomous_governance_check.py`**, **`make autonomous-governance-check`**, and **`make multi-agent-governance-check`** (each includes **`make gate`**). Deterministic JSON with **`ok`**, **`score`**, **`checks`**, **`failures`**, **`warnings`**, **`checked_paths`**, **`multi_agent`**, **`version`** (sorted keys with `--json`).
- **Public launch and ecosystem standardization driver (stdlib, no network)** — **`docs/launch/`**, **`examples/launch/`**; **`make public-launch`**, **`make public-launch-manifest`**, **`make standardization-readiness-snapshot`**, **`make public-launch-readiness-score`**, **`make public-launch-report`**, and aggregated **`make public-launch-check`** (includes **`make gate`**). OSS CI emits **`public-launch.json`**, **`public-launch-manifest-validation.json`**, **`standardization-readiness-snapshot-validation.json`**, **`public-launch-readiness-score.json`**, and **`public-launch-report.md`**.
- **Research and academic publication driver (stdlib, no network)** — **`research/`** JSON bundle, **`docs/research/`**, **`examples/research/`**; **`python3 scripts/validate_research_manifest.py --json`**, **`python3 scripts/research_package_check.py --json`**, **`make research-package-check`**, and **`make academic-publication-check`** (chains **`research-package-check`** and **`make gate`**). Start with **`docs/research/README.md`**, **`docs/research/benchmark-methodology.md`**, and **`docs/research/reproducibility.md`**.
- **Research support and operational evidence (stdlib, no network)** — quantitative feasibility notes, synthetic audit microbenchmarks, threat-matrix sample JSON, legal evidentiary positioning, privacy patterns, provider cooperation roadmap, scalability docs; **`docs/research/research-support-manifest.json`**, **`python3 scripts/research_support_check.py --json`**, **`make research-support-check`**, granular **`make microbenchmark-check`**, **`make threat-model-check`**, **`make legal-positioning-check`**, **`make privacy-architecture-check`**, **`make provider-cooperation-check`**, **`make scalability-patterns-check`**, and aggregate **`make manuscript-evidence-check`** (runs **`scripts/manuscript_evidence_runner.py`**, including **`make gate`**). CI writes JSON artefacts to **`.oss-ci-out/`** when **`MANUSCRIPT_EVIDENCE_DIR`** is set. Audit report: **`docs/reports/research-support-and-operational-evidence.md`**.
- **Developer integrations and automation platform driver (stdlib, no network)** — **`docs/integrations/`** guides, **`docs/integrations/developer-integrations-manifest.json`**, **`examples/integrations/`**, automation pack sample **`examples/integrations/sample-automation-pack.json`**, validators **`scripts/validate_developer_integrations_manifest.py`**, **`scripts/validate_automation_pack.py`**, **`scripts/generate_automation_pack_summary.py`**, and aggregated **`make developer-integrations-check`** and **`make sdk-ecosystem-check`**.
- **Marketplace and developer platform driver (stdlib, no network)** — **`examples/marketplace/`**; **`make marketplace`**, **`make marketplace-check`**, **`make marketplace-manifest`**, **`make extension-package`**, and **`make marketplace-listing`**.
- **Policy pack marketplace driver (stdlib, no network)** — **`marketplace/manifest.json`**, **`registry/policy-pack-catalog.json`**, **`examples/marketplace/*/`** packs, **`python3 scripts/validate_policy_pack.py`**, **`python3 scripts/registry_check.py`**, **`make policy-pack-check`**, **`make registry-check`**; catalog validation via **`python3 scripts/validate_marketplace_manifest.py --json --manifest marketplace/manifest.json`**.
- **Customer analytics and expansion intelligence driver (stdlib, no network)** — **`docs/analytics/`** and **`examples/customer-analytics/`**; **`make customer-analytics`**, **`make customer-analytics-manifest`**, **`make customer-health-score`**, **`make executive-business-review`**, and aggregated **`make customer-analytics-check`**.
- **Revenue intelligence and customer success analytics driver (stdlib, no network)** — **`revenue/`** JSON, **`docs/revenue/`**, **`examples/revenue/`**; **`make revenue-intelligence`**, **`make revenue-intelligence-manifest`**, **`make revenue-intelligence-check`**, and **`make customer-success-check`**.
- **Evidence quality, provenance, and dataset governance driver (stdlib, no network)** — **`docs/evidence-quality/`** and **`examples/evidence-quality/`**; **`make evidence-quality`**, **`make evidence-quality-manifest`**, **`make dataset-provenance-snapshot`**, **`make evidence-quality-score`**, **`make dataset-governance-report`**, and aggregated **`make evidence-quality-check`** (includes **`make gate`**).
- **Release engineering driver (stdlib, no network)** — **`examples/releases/`**; **`make release-manifest`**, **`make validate-changelog`**, **`make generate-release-notes`**, **`make release-readiness-report`**, and aggregate **`make release-readiness-check`** (chains **`release-operations-check`**, manifest/changelog validators, readiness JSON, **`docs-links-strict`**, and **`gate`**).
- **Local demo contract** — read-only **`make local-demo`** vs **`make fail-closed-demo`**, exit codes, and env vars: **`examples/local-demo/CONTRACT.md`**.
- **Public documentation (production)** — reader-facing **`/docs`** and **`/help`** on **[govbase.dev](https://govbase.dev)** are served by the **`dashboard/`** Next.js app from canonical Markdown in **`docs/`** (same files as in GitHub). The public **`/`** landing explains **How GovAI Works** (icon cards + flow) without requiring Supabase connectivity. Local preview: `cd dashboard && npm ci && npm run dev`. Authenticated **tenant console** UI: **`/tenant-console`** loads **`GET /api/tenant-console/snapshot`** (stable **`snapshot_version: 3`** JSON, including **`ai_decision_audit`** with per-trace integrity and verdict rollups when bound to Postgres). Set **`AIGOV_AUDIT_URL`** or **`NEXT_PUBLIC_GOVAI_API_BASE_URL`**. The audit service also returns shared **`product_positioning`** on **`GET /`**, **`GET /status`**, and **`GET /api/me`**. See **`docs/tenant-console/overview.md`**.

## Cursor / IDE integration

GovAI ships a **repository-bundled Cursor plugin pack** under **`.cursor-plugin/`** (rules, Agent skills in **`skills/<name>/SKILL.md`**, Marketplace-oriented **`plugin.json`**, plugin-level **`mcp.json`**, and a local **stdio MCP** bridge to **`mcp/govai_mcp_server.py`**). It aligns local agent behaviour with the same scripts and gates used in CI; **hosted audit services, Rust enforcement, and database policy remain authoritative** for production compliance.

- **Start here:** [`.cursor-plugin/quickstart.md`](.cursor-plugin/quickstart.md) — install steps, MCP wiring, first gate, troubleshooting.
- **Reference:** [`.cursor-plugin/README.md`](.cursor-plugin/README.md) — tools, security model, and marketplace readiness notes.
- **Tutorial:** [`docs/tutorials/cursor-plugin-walkthrough.md`](docs/tutorials/cursor-plugin-walkthrough.md) — guided walkthrough.

Validate the bundle from the repository root (same check as CI):

```bash
make cursor-plugin-check
```

**Workspace `.cursor/`:** this repository does **not** commit machine-local **`.cursor/`** trees (rules merge, skills paths, and **`mcp.json`** vary by developer). Use the checked-in **`.cursor/mcp.json.example`** as a starting point, merge **`.cursor-plugin/examples/local-config.json`**, or align with **`.cursor-plugin/mcp.json`** / **`plugin.json`** `mcpServers`; see the quickstart for copy commands. Do not commit secrets or user-specific absolute paths.

## Local fail-closed demo (Docker, copy-paste)

This path proves **incomplete evidence → `govai check` exits with code 3** (BLOCKED contract), using the same **`examples/blocked_deployment.sh`** script exercised in CI. The wrapper script exits **0** only after it confirms **`govai check`** returned exit code **3** (so your shell shows `0` from `bash` when the demo succeeded).

**Prerequisites:** Docker Compose v2, Python **3.10+**, this repository cloned.

**1. Start Postgres + audit service** (repository root):

```bash
docker compose up -d --build
```

**2. Wait for readiness** (`GET /ready` is on the **unauthenticated** audit router; HTTP **200** means Postgres, migrations, and ledger checks passed):

```bash
curl -fsS http://127.0.0.1:8088/ready
```

Root **`docker-compose.yml`** sets **`GOVAI_API_KEYS`** to include the bearer secret **`test-key`**. Your CLI must use the **same** value.

**3. Install the `govai` CLI** (venv inside `python/`, matches contributor docs):

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
cd ..
```

**4. Run the blocked deployment example** (repository root) **or** the Makefile wrapper (same behaviour):

```bash
export GOVAI_AUDIT_BASE_URL=http://127.0.0.1:8088
export GOVAI_API_KEY=test-key
bash examples/blocked_deployment.sh
```

Equivalent wrapper (JSON summary on stdout, progress on stderr):

```bash
export GOVAI_AUDIT_BASE_URL=http://127.0.0.1:8088
export GOVAI_API_KEY=test-key
make fail-closed-demo
```

**Expected:**

- **`govai check`** prints a **BLOCKED** outcome and exits with code **3** (the script checks this).
- The **`bash examples/blocked_deployment.sh`** process exits **0** after verification (`blocked_deployment_example: OK ...` on stderr).

**5. Cleanup:**

```bash
docker compose down
```

More context: **`examples/docker-compose-local-demo/README.md`**, canonical contributor setup **`docs/project/local_development.md`**, and read-only probes **`make local-demo`** (no evidence POST).

## Troubleshooting and operator docs

- **Troubleshooting matrix (customers + operators)**: `docs/troubleshooting.md`
- **Operator runbook (hosted/self-hosted)**: `docs/operator-runbook.md`
- **Runtime governance (preview / `POST /v1/runtime/evaluate`)**: default **`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT=off`**; optional **`shadow`** or **`enforced`** — see `docs/governance/runtime_enforcement_gate.md` and `docs/governance/runtime_integration.md`. Tenant allowlist (**`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT_TENANTS`**) scopes hard blocking under **`enforced`**. Operational snapshot: **`GET /ready`** and **`GET /status`** include **`runtime_governance_enforcement`** (informational; not an infra readiness signal on its own).

## Quickstart (5 minutes)

Choose one:

- **Hosted (recommended)**: follow `docs/customer-onboarding-10min.md` (canonical hosted onboarding: `BLOCKED → VALID`, then export).
- **Local (Docker, this repo)**: continue below (for local evaluation / contributor setup).

1. Clone the repo

```bash
git clone https://github.com/MonikaDvorackova/govai-core.git
cd govai-core
```

2. Run GovAI (Docker)

```bash
docker compose up -d --build
```

3. Check health

```bash
curl http://127.0.0.1:8088/health
```

Expected output:
HTTP 200
`{"ok":true}`

The audit service is **fail-fast at startup**: Postgres must be reachable and correctly configured **before** HTTP listens. **`GET /health`** does not hit the database, but it is **only available after** that startup succeeds — it is **liveness-only**, not proof that Postgres or the ledger are still healthy. Use **`GET /ready`** for operational readiness (Postgres + migrations + writable ledger); see **`docs/hosted-backend-deployment.md`** (“HTTP startup and operational probes”).

4. What you just did
- started the audit service
- exposed the API on port `8088`
- ready to receive evidence and run checks

## Coming from Discord?

Join the community:
https://discord.gg/sRBSafRtE

If you joined from Discord:
- ask questions in `#govai-help`
- share your use case in `#use-cases`

## Product Scope

**Protected branches:** merges that must imply artefact-bound hosted validation should require **`.github/workflows/compliance.yml`** (**`govai-compliance-gate`**) — not **`govai-smoke.yml`** (manual smoke only) or **`govai check` alone**. Details: **[docs/github-action.md](docs/github-action.md)**.

It:

- accepts evidence via POST /evidence
- enforces policy constraints at write time
- produces deterministic decisions via GET /compliance-summary
- blocks CI or automation when verdict != VALID (when wired to a gate)
- exports audit data via GET /api/export/:run_id
- optionally enforces hosted Stripe subscription state for metered APIs (see docs/billing.md)

**Multi-tenant ledger:** the ledger tenant is always derived from **API key mapping** (`GOVAI_API_KEYS_JSON` on the server). **`X-GovAI-Project` / `GOVAI_PROJECT` are metadata** (metering, labels, client hints) and **do not** determine which tenant ledger is used.

Guarantees:

- deterministic decision for given evidence + policy_version
- append-only evidence log
- hash chaining integrity

Non-guarantees:

- not a legal certification
- not full compliance coverage
- does not generate missing evidence

## Bring your own policy

GovAI is **policy-agnostic**: the engine enforces evidence completeness and deterministic decision semantics, not a specific legal framework.
Policy is a **configuration layer** that compiles into a flat `required_evidence` set (static mapping, no runtime logic).
Customers can replace the AI Act mapping with an internal policy module **without changing the core GovAI engine**.
The engine remains deterministic: evidence log + policy requirements → `GET /compliance-summary` → `VALID` / `BLOCKED` / `INVALID`.
Use `govai policy compile --path <policy.yaml>` to inspect the flat `required_evidence` set for a policy module.
See `docs/customer-policy-modules.md` and `docs/policies/`.

## How GovAI decides what is required

GovAI compiles “what is required” into a deterministic **flat set**:

`discovery (context detection)` + `policy modules (static mapping)` → `required_evidence (flat set)` → existing GovAI engine → verdict (`VALID` / `INVALID` / `BLOCKED`)

Key constraints:

- discovery is heuristic-only and deterministic (no ML, no scoring)
- policy modules are static mappings (no conditionals)
- the core decision semantics and API contracts remain unchanged

See:

- `docs/discovery-v2.md`
- `docs/customer-policy-modules.md`

## When to use GovAI

- deploying ML models via CI/CD
- enforcing approval workflows before release
- requiring audit evidence for decisions

## GovAI Platform (not in GovAI Core)

Commercial hosting, billing, pricing, dashboard ACL, onboarding, and managed tenant provisioning belong to the **GovAI Platform** product (separate from this repository). Reference material may appear under `docs/pricing/`, `docs/billing/`, `docs/hosted/`, and `dashboard/` for historical context only.

## Decision states

VALID:  
All required evidence present. Deployment allowed.

INVALID:  
Server verdict when **evaluation explicitly failed** (`evaluation_passed == false`). Deployment rejected.

BLOCKED:  
Not eligible for promotion: **missing required evidence**, **missing risk/human approval**, **not yet promoted**, or other prerequisites (digest/export/trace) not satisfied. Deployment halted.

`BLOCKED` can occur when required evidence is missing **or** when approval/promotion prerequisites are not satisfied (in that case `missing_evidence` can be `[]`; see `blocked_reasons`).

## Install

**GovAI CLI (PyPI — official):**

```bash
python -m pip install --upgrade pip
python -m pip install "aigov-py==0.2.1"
```

**Repository contributors** (editable install from a clone of this repo):

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd ..
```

## Quickstart

Start the audit service, emit evidence, and read the authoritative decision from `GET /compliance-summary`.

Quickstarts:

- `docs/customer-onboarding-10min.md` (hosted customer onboarding — canonical)
- `docs/quickstart-5min.md` (local demo)
- `docs/customer-quickstart.md` (legacy customer / CI quickstart)
- `docs/pilot-onboarding.md` (private pilot onboarding)
- `docs/billing.md` (minimal Stripe webhook + usage summary)
- `docs/product/differentiation.md` (GovAI as **decision enforcement** vs supply-chain attestation)

## Hosted pilot prerequisites

GovAI is **ready for GitHub Marketplace draft and hosted pilot onboarding**.

It is **not yet a full self-serve SaaS**.

Hosted backend and API key provisioning are still **operator managed**.

Repeatable operator + customer steps (pilot runbook):

- `docs/hosted-pilot-runbook.md`


Minimum hosted-pilot path (what must exist before a new pilot user can reach `VALID`):

- **How a pilot user gets `base_url`**: the operator provides a hosted HTTPS audit API base URL (the GovAI audit service), for example `https://audit.example.com`.
- **Example**: `GOVAI_AUDIT_BASE_URL=https://audit.govbase.dev`
- **How a pilot user gets an API key**: the operator provisions and distributes a bearer token (one per customer/team). This is manual or semi-automated in a pilot.
- **How a pilot user creates/receives `run_id`**: the pilot user generates a UUID (or the operator provides one). The same `run_id` must be reused for evidence submission, the CI gate, and export.
- **How evidence is submitted**: evidence events are appended to the hosted audit service via `POST /evidence` (either via `govai run demo-deterministic` for onboarding, or via your CI/app pipeline emitting evidence events).
- **How the run reaches `VALID`**: the run transitions `BLOCKED → VALID` only after all required evidence is appended for the same `run_id` and policy rules pass; the authoritative source is `GET /compliance-summary`.
- **How CI gate checks `VALID`**: the **published composite GitHub Action** (root `action.yml`) runs **`govai submit-evidence-pack`** then **`govai verify-evidence-pack`** (digest continuity via hosted **`GET /bundle-hash`**, then **`GET /compliance-summary`** for a **`VALID`** verdict). By default it passes **`--require-export`** so **`GET /api/export/:run_id`** must cross-check unless callers set **`require_export: false`**. See **`docs/github-action.md`**.

## Canonical flow (discovery → requirements → BLOCKED → evidence → VALID → export → CI)

GovAI is designed around **one evidence run id** (`run_id`) and **one authoritative decision projection** exposed through `GET /compliance-summary`. Use CI gates when you also need artefact-bound digests.

Canonical customer flow:

1. **Discovery finds AI usage** (signals are recorded as evidence for a specific `run_id`).
2. **GovAI derives requirements** from the current policy and any discovery signals (required evidence can increase when discovery indicates AI usage).
3. **The run is `BLOCKED` while it is not eligible for promotion** (the summary reports `verdict: BLOCKED` and explains why, via `missing_evidence` and/or `blocked_reasons`).
4. **The customer submits the missing evidence** for the same `run_id` (additional events are appended via `POST /evidence`).
5. **The run becomes `VALID`** once the required evidence is present and policy rules pass (the authoritative source is still `GET /compliance-summary`).
6. **The customer exports audit JSON** for archiving and review (`govai export-run` or `GET /api/export/<run_id>`).
7. **The CI gate passes only on `VALID`** for the artefact-bound path above (verify exit **`0`** only when digest + export rules (if required) + verdict **`VALID`**). For a **lighter** readout without digest/export binding, **`govai check`** still calls **`GET /compliance-summary`** and exits non-zero unless the verdict is **`VALID`** — that is not the same guarantee as **`verify-evidence-pack`**.

## Why GovAI

If you cannot prove why a specific model version was deployed, you do not have a deployment decision — you have a story.

GovAI makes deployment decisions verifiable and reproducible by:

- accepting lifecycle events as structured evidence (POST /evidence) into an append-only ledger
- enforcing policy at write time (out-of-order or missing prerequisites are rejected)
- projecting a single authoritative decision for a run: GET /compliance-summary → VALID / INVALID / BLOCKED

Decision authority: the only authoritative decision source is GET /compliance-summary. The database, UI, workflow rows, and CLI are consumers of that decision; they do not derive it.

## Example: ML pipeline audit

This example shows the decision path for an expense classification release candidate:

events → append-only evidence → GET /compliance-summary → decision

Key identifiers:

- ai_system_id: expense-ai
- dataset_id: expense_dataset_v1
- model_version_id: expense_model_v3
- risk_id: risk_expense_model_v3

Minimal event flow (in order):

1. data_registered (dataset identity + fingerprint)
2. model_trained (ties a model version to the run)
3. evaluation_reported (metrics as evidence; policy decides pass/fail)
4. risk_recorded + risk_reviewed (explicit risk linkage and review outcome)
5. human_approved (named approval)
6. model_promoted (release intent, only accepted when prerequisites are satisfied)

The result is never inferred locally. The decision is read from:

    curl -sS "http://127.0.0.1:8088/compliance-summary?run_id=$GOVAI_RUN_ID"

and interpreted only by its returned fields (verdict, current_state, and the policy metadata).

Result:

GET /compliance-summary → verdict: VALID

Because:

- evaluation passed
- risk reviewed
- human approved
- promotion event accepted

Non-happy paths:

- INVALID → evaluation explicitly failed
- BLOCKED → not eligible for promotion (missing evidence and/or missing approval/promotion prerequisites)

## CI Integration

For **production** merges, prefer the **artefact-bound** path: **`submit-evidence-pack`** + **`verify-evidence-pack`** (as in **`docs/github-action.md`** and this repo’s **`compliance.yml`**), including export cross-check when **`require_export`** is left at its default **`true`** on the composite action.

**`govai check`** is a **convenience readout**: it does not bind CI artefacts to the ledger digest; it calls **`GET /compliance-summary`** and exits non-zero unless the server verdict is **`VALID`**. Use it for quick checks or smoke, not as a substitute for **`verify-evidence-pack`** when you need cryptographic continuity to CI outputs.

Use **one** GovAI evidence run id (`GOVAI_RUN_ID`) for every evidence submission, the gate, and export.

If you are onboarding a new pilot customer, follow `docs/hosted-pilot-runbook.md` end-to-end first (hosted backend + key + deterministic demo + CI gate + export).

### Minimal copy-paste GitHub Actions workflow (strict gate)

1) Set repository configuration in **Settings → Secrets and variables → Actions**:

- Variable `GOVAI_AUDIT_BASE_URL`: `https://<your GovAI audit API base URL>`
- Variable `GOVAI_RUN_ID`: `<your evidence run id>` (not GitHub’s `github.run_id`)
- Secret `GOVAI_API_KEY`: `<your API key>` (required; missing key fails CI immediately)

2) Wire the **composite action** after you have a directory of CI evidence artefacts (`evidence_digest_manifest.json` and `<run_id>.json`). Example step (paths depend on your artefact download layout):

```yaml
      - name: GovAI artefact-bound gate (submit + verify digest + VALID)
        uses: MonikaDvorackova/govai-core@v1
        with:
          run_id: ${{ vars.GOVAI_RUN_ID }}
          artifacts_path: ${{ github.workspace }}/downloaded-artifacts
          base_url: ${{ vars.GOVAI_AUDIT_BASE_URL }}
          api_key: ${{ secrets.GOVAI_API_KEY }}
```

In **this** repo, **`.github/workflows/compliance.yml`** is the production artefact-bound gate; **`.github/workflows/govai-smoke.yml`** is an optional **manual synthetic smoke** workflow only.

See `docs/github-action.md` for inputs, exit codes, and hosted semantics.

### First-time end-to-end (reach `BLOCKED` then `VALID`)

To validate your setup before relying on the CI gate, run the hosted deterministic onboarding flow locally against your GovAI audit API:

```bash
python -m pip install --upgrade pip
python -m pip install "aigov-py==0.2.1"

export GOVAI_AUDIT_BASE_URL="https://<your GovAI audit API base URL>"
export GOVAI_API_KEY="YOUR_API_KEY"

export GOVAI_RUN_ID="$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"

export GOVAI_DEMO_RUN_ID="$GOVAI_RUN_ID"
govai run demo-deterministic
govai check --run-id "$GOVAI_RUN_ID"
```

Expected behavior:

- First, the run reports `verdict: BLOCKED` and explains why it is not eligible for promotion (missing evidence and/or `blocked_reasons`).
- After the demo appends the remaining evidence for the same `run_id`, the run becomes `verdict: VALID`.
- The CI gate passes only when the server verdict is `VALID`.

## Operator-hosted backend (Docker Compose quickstart)

This repo includes a minimal operator-hosted path to run the Rust audit service + Postgres locally via Docker Compose (intended as a **quickstart**, not production hardening).

```bash
docker compose up -d --build
```

Smoke test:

```bash
curl -sS http://127.0.0.1:8088/status
curl -sS http://127.0.0.1:8088/health
```

Details and limitations: `docs/hosted-backend-deployment.md` → “Operator-hosted quickstart (Docker Compose)”.

## Audit export (machine-readable)

To export a run into a **stable JSON** document that includes the **decision** fields and **hashes** (bundle SHA-256 + append-only chain hashes), use:

    govai export-run --run-id "$GOVAI_RUN_ID"

HTTP equivalent:

    curl -sS "http://127.0.0.1:8088/api/export/$GOVAI_RUN_ID"

Note: a run can be `BLOCKED` even when `missing_evidence: []` if approval/promotion prerequisites are not satisfied; the export explains this via `decision.blocked_reasons`. See `docs/examples/audit_export_v1.example.json`.

## Core vs Non-Core

- Core: the append-only audit log, policy enforcement at POST /evidence, and the single authoritative projection GET /compliance-summary (decision + state).
- Non-Core: workflow tables/queues and helper tooling/CLI wrappers. They may display or transport evidence, but they do not decide.

## API usage tiers

Hosted platform plans expose usage limits via `GET /usage` (runs and events per billing period). Commercial packaging is described in [docs/pricing/index.md](docs/pricing/index.md); engineering limits follow your deployment configuration and order form.

## Auditability and Trust

- append-only logs
- hash chaining (prev_hash → record_hash)
- deterministic decision (policy_version)
- exportable audit JSON

Minimal definitions and non-claims:

- `docs/trust-model.md`
- `docs/cvut-teaching.md` (teaching-friendly)

## Current maturity

GovAI is **ready for hosted pilots with manual or semi-automated onboarding** (for example: an admin provisions `GOVAI_AUDIT_BASE_URL` and an API key, and you run the canonical onboarding flow).

It is **not yet a full self-serve SaaS** (no productized signup, automated provisioning, or account lifecycle).

Hosted **Stripe billing** is supported for operator-managed pilots (checkout, webhooks, usage reporting); self-serve checkout and full SaaS lifecycle are not productized yet (see [docs/billing.md](docs/billing.md)).

## Community and Launch

Publication-ready **channel playbooks**, **FAQ**, and **positioning** live under `docs/launch/` (see [launch checklist](docs/launch/launch-checklist.md)). **Integration examples** and **reference hubs** explain practical adoption paths without duplicating the canonical GitHub Action spec.

**Launch materials**

- [Product Hunt](docs/launch/product-hunt.md) · [Hacker News](docs/launch/hacker-news.md) · [Reddit](docs/launch/reddit.md) · [LinkedIn](docs/launch/linkedin.md)
- [Community outreach](docs/launch/community-outreach.md) · [Design partners](docs/launch/design-partners.md)
- [FAQ](docs/launch/faq.md) · [Competitive positioning](docs/launch/competitive-positioning.md) · [Launch checklist](docs/launch/launch-checklist.md)

**Reference examples**

- [GitHub Actions integration](docs/examples/github-actions-integration.md) — [`examples/reference/github-actions/README.md`](examples/reference/github-actions/README.md)
- [Enterprise deployment](docs/examples/enterprise-deployment.md) — [`examples/reference/enterprise-deployment/README.md`](examples/reference/enterprise-deployment/README.md)
- [AI Act–oriented workflow (illustrative)](docs/examples/ai-act-compliance-workflow.md) — [`examples/reference/ai-act-compliance/README.md`](examples/reference/ai-act-compliance/README.md)

**Reference implementation kits (runnable / copy-paste)**

- Index: [reference implementations](docs/adoption/reference-implementations.md) · [quickstart matrix](docs/adoption/quickstart-matrix.md) · [operator evaluation guide](docs/adoption/operator-evaluation-guide.md)
- [`examples/adoption/github-actions-ci-gate/`](examples/adoption/github-actions-ci-gate/) — workflow + sample JSON (default job needs **no secrets**)
- [`examples/adoption/self-hosted-enterprise/`](examples/adoption/self-hosted-enterprise/) — Compose + `.env.example`
- [`examples/adoption/ai-act-evidence-workflow/`](examples/adoption/ai-act-evidence-workflow/) — interchange JSON samples
- [`examples/adoption/standards-conformance-kit/`](examples/adoption/standards-conformance-kit/) — offline `run-conformance.sh`

**Contributor growth**

- [First external contributor playbook](docs/community/first-external-contributor-playbook.md) · [Maintainer outreach checklist](docs/community/maintainer-outreach-checklist.md) · [Contributor recognition](docs/community/contributor-recognition.md)

**Readiness checks**

- `make launch-readiness` — core launch narratives present
- `make ecosystem-adoption-check` — launch + examples + community + consolidated audit report paths
- `make adoption-kits-check` — adoption kits + `docs/adoption/` + offline conformance validation
- `make reference-implementations-check` — `docs/adoption/` trio only

**Repository cleanup audit:** [`docs/reports/repo-debt-audit-and-cleanup.md`](docs/reports/repo-debt-audit-and-cleanup.md) (launch + adoption kits)

## Marketplace draft checklist

- **root action exists**: `action.yml` exists at the repository root.
- **strict gate fails on missing config**: missing `run_id`, `base_url`, or `api_key` fails fast.
- **gate passes only on VALID**: the action exits 0 only when the backend verdict is `VALID`.
- **BLOCKED output explains why promotion is blocked**: `BLOCKED` is surfaced as a compliance failure, not a silent skip (it may be missing evidence and/or missing approval/promotion prerequisites).
- **hosted base URL and API key are required**: customers must configure `GOVAI_AUDIT_BASE_URL` and `GOVAI_API_KEY`.
- **support contact is listed**: support contact for Marketplace users is `support@govbase.dev`.

---

# Contributors and community

Contributions to **GovAI Core** belong in this repository. See [`CONTRIBUTING.md`](CONTRIBUTING.md), [`GOVERNANCE.md`](GOVERNANCE.md), and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Do not weaken ledger-authoritative invariants documented there.

## Contributor onboarding

- Contributor quickstart: `docs/project/contributor_quickstart.md`
- Contributing guide: `CONTRIBUTING.md`
- Code of conduct: `CODE_OF_CONDUCT.md`
- Local env template (no secrets): `.env.example`
- **Local development (clone, venv, Docker, gates, tests)**: `docs/project/local_development.md`
- Security policy: `SECURITY.md`

## Community operations

Structured **contributor funnel**, **issue triage**, maintainer cadence, label playbooks (`good first issue`, `help wanted`), adoption feedback, and project-board routines:

- [docs/community/contributor-funnel.md](docs/community/contributor-funnel.md)
- [docs/community/issue-triage.md](docs/community/issue-triage.md)
- [docs/community/maintainer-operating-model.md](docs/community/maintainer-operating-model.md)

Validate locally (stdlib only):

```bash
python3 scripts/community_operations_check.py
make community-operations-check
make contributor-funnel-check
```

## Project governance

- Roadmap: `docs/project/roadmap.md`
- Label taxonomy: `docs/project/label_taxonomy.md`
- Research and ecosystem governance: `docs/governance/research_and_ecosystem.md`
- Ecosystem standards (schemas, CLI, examples): `docs/standards/README.md`

## Contribution areas

We welcome contributions in:

- Rust services
- Python SDKs
- governance enforcement
- CI/CD integrations
- documentation
- examples
- deployment tooling
- architecture diagrams

## Good first contributions

New contributors are encouraged to look for issues labeled:

- `good first issue`
- `help wanted`
- `documentation`
- `examples`

