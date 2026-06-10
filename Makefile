SHELL := /bin/bash
-include .env
export

AIGOV_MODE ?= ci

.PHONY: \
	FORCE \
	audit audit_bg audit_stop audit_restart audit_logs require_audit_url \
	status verify verify_log \
	run \
	require_run ensure_dirs ensure_reports_dir new_run report_new report_prepare report_prepare_new ensure_evidence pr_report pr_report_commit db_ingest \
	check_audit \
	report_template report_init report_fill \
	bundle verify_cli evidence_pack \
	emit_event \
	flow flow_full \
	pr_prepare gate core-runtime-examples-check reference-integrations-check reconstructible-demo-check runtime-packaging-check runtime-observability-check lineage-governance-check \
	runtime-sdk-check developer-integrations-platform-check \
	audit_close \
	demo demo_new \
	env_check \
	engineering_loc \
	oss-health oss-metrics docs-links docs-links-strict oss-diagnostics oss-ecosystem-check \
	commercial-readiness commercial-readiness-check \
	security-trust trust-manifest trust-chain-check immutable-trust-check enterprise-readiness-check \
	runtime-audit-metrics-check disaster-recovery-check evidence-map-check security-program-check stabilization-readiness-check \
	standards-conformance governance-standards-check \
	pilot-execution pilot-manifest \
	revenue-manifest revenue-roi revenue-proposal revenue-enablement \
	community-operations-check contributor-funnel-check \
	go-to-market-check \
	launch-readiness ecosystem-adoption-check \
	adoption-kits-check reference-implementations-check \
	developer-integrations-check public-sdk-packages-check sdk-ecosystem-check \
	typescript-client-check iso-42001-readiness-check \
	customer-operations customer-operations-manifest production-readiness-checklist production-operations-check \
	partner-ecosystem partner-ecosystem-manifest partner-certification-package \
	partner-ecosystem-check integration-marketplace-check \
	product-analytics-check growth-instrumentation-check \
	regulatory-evidence regulatory-manifest ai-act-obligations regulatory-export regulatory-check \
	iso-42001-manifest iso-42001-clause-index iso-42001-readiness-check \
	registry-check \
	observability observability-manifest operational-snapshot operational-health-score operational-intelligence-report observability-check \
	runtime-safety runtime-safety-manifest runtime-safety-snapshot runtime-safety-score runtime-safety-report runtime-safety-check \
	agent-governance agent-governance-manifest agent-delegation-snapshot agent-governance-score agent-governance-report agent-governance-check \
	autonomous-governance-check multi-agent-governance-check \
	marketplace marketplace-manifest extension-package marketplace-listing marketplace-check policy-pack-check \
	customer-analytics customer-analytics-manifest customer-health-score executive-business-review customer-analytics-check \
	policy-intelligence policy-intelligence-manifest governance-control-snapshot policy-coverage-score governance-control-report policy-intelligence-check \
	control-plane control-plane-check enterprise-governance-check control-plane-manifest governance-posture-snapshot governance-posture-score control-plane-report governance-posture-check \
	developer-integrations developer-integrations-manifest automation-pack automation-pack-summary developer-integrations-platform-check \
	release-operations-check release-readiness-check \
	release-manifest validate-changelog generate-release-notes release-readiness-report \
	evidence-quality evidence-quality-manifest dataset-provenance-snapshot evidence-quality-score \
	dataset-governance-report evidence-quality-check \
	local-demo local-demo-curl fail-closed-demo \
	cursor-plugin-validate cursor-plugin-smoke cursor-plugin-check \
	model-risk model-risk-manifest model-evaluation-snapshot model-risk-score model-assurance-report model-risk-assurance-check \
	hosted-platform hosted-platform-manifest hosted-readiness-snapshot \
	hosted-readiness-score hosted-readiness-export hosted-platform-check \
	hosted-saas-readiness hosted-saas-readiness-check \
	conformity-workflow-check regulatory-workflow-check \
	multi-tenant multi-tenant-check tenant-isolation-check \
	functions-v2-check npm-typescript-publishing-check \
	public-launch public-launch-manifest standardization-readiness-snapshot \
	public-launch-readiness-score public-launch-report public-launch-check

.PHONY: discovery_scan
discovery_scan:
	cd python && . .venv/bin/activate && \
		python -m aigov_py.cli discovery scan --path ..

FORCE:

# Optional operator-provided audit HTTP base URL (GovAI Platform or customer self-host).
# GovAI Core does not start, background-manage, or readiness-poll a hosted audit server.
AUDIT_URL ?= $(GOVAI_AUDIT_BASE_URL)

# Legacy: GOVAI_AUTO_MIGRATE applied only when using an external Platform-operated runtime.
GOVAI_AUTO_MIGRATE ?= true

# Explicit binary: this crate ships multiple `[[bin]]` targets; `cargo run` without `--bin` fails.
AIGOV_AUDIT_BIN ?= portable_evidence_digest_once

# ================================
# Env debug
# ================================

env_check:
	@echo "PWD=$$(pwd)"
	@echo "SUPABASE_URL=$(SUPABASE_URL)"
	@echo "SUPABASE_SERVICE_ROLE_KEY=$$(if [ -n "$(SUPABASE_SERVICE_ROLE_KEY)" ]; then echo "SET"; else echo "MISSING"; fi)"
	@ls -la .env 2>/dev/null || true

# Compliance "gate" check used by CI:
# ensure that generated audit reports include the minimum required sections.
gate:
	@python3 scripts/gate_reports.py

# Adoption examples must not call platform-only HTTP routes (drift vs govai_api.rs).
core-runtime-examples-check:
	@python3 scripts/check_core_runtime_example_routes.py

reference-integrations-check:
	@python3 scripts/check_reference_integrations.py

reconstructible-demo-check:
	@python3 scripts/check_reconstructible_demo.py

runtime-packaging-check:
	@python3 scripts/check_runtime_packaging.py

runtime-observability-check:
	@python3 scripts/check_runtime_observability.py

lineage-governance-check:
	@python3 scripts/check_lineage_governance_graph.py

# Registered interchange conformance checks.
standards-conformance:
	@cd python && python3 -m pytest tests/test_standards_conformance.py -q

# Validates shipped interchange examples against the explicit registry-backed validators.
governance-standards-check:
	@echo "governance-standards-check is not available in GovAI Core; platform standards validation belongs to the proprietary platform repository."

oss-health:
	@python3 scripts/repo_health_check.py

oss-metrics:
	@python3 scripts/oss_metrics.py

docs-links:
	@python3 scripts/validate_docs_links.py

docs-links-strict:
	@python3 scripts/validate_docs_links.py --strict

oss-ecosystem-check:
	@python3 benchmarks/auditability-failures/run_benchmark.py
	@python3 scripts/validate_docs_links.py
	@python3 scripts/gate_reports.py
	@echo "oss-ecosystem-check: OK"

# oss-diagnostics intentionally excludes local-demo (requires a running audit service).
# Uses docs-links-strict so CI and local runs fail on broken relative links in README + docs/.
# oss_diagnostics docs/reports gate: three-dot vs origin/staging plus worktree fallback (override base with GOVAI_OSS_DIAGNOSTICS_BASE_REF).
oss-diagnostics:
	@$(MAKE) oss-health && $(MAKE) oss-metrics && $(MAKE) docs-links-strict && $(MAKE) functions-v2-check && python3 scripts/oss_diagnostics.py --json >&2 && $(MAKE) gate

# Deterministic JSON validation for GovAI Functions 2.0 flight-pack fixtures (stdlib).
functions-v2-check:
	@python3 scripts/validate_govai_functions_v2_pack.py --strict examples/govai-functions-2/sample-flight-pack.v1.json

# TypeScript SDK npm publishing readiness (metadata, docs, manifest; no network; no npm publish).
npm-typescript-publishing-check:
	@python3 scripts/npm_typescript_publishing_check.py

# Commercial documentation + demo assets (stdlib path checks; no network).
commercial-readiness:
	@python3 scripts/commercial_readiness_check.py

# Aggregated commercial gate: path checks + report heading gate.
commercial-readiness-check:
	@$(MAKE) commercial-readiness && $(MAKE) gate

# Enterprise security and trust documentation presence (stdlib script; deterministic JSON with --json).
security-trust:
	@python3 scripts/security_trust_check.py

# Validate docs/trust/trust-manifest.json (required fields + referenced paths).
trust-manifest:
	@python3 scripts/validate_trust_manifest.py

# Cryptographic trust artefacts (trust/*.json + examples/trust) — stdlib validator; deterministic JSON with --json.
trust-chain-check:
	@python3 scripts/trust_chain_check.py

# Trust artefact validation plus audit report heading gate.
immutable-trust-check: trust-chain-check gate
	@echo "immutable-trust-check: OK"

# Enterprise readiness gate: security/trust diagnostics + trust manifest + commercial readiness + full OSS developer experience checks.
enterprise-readiness-check:
	@$(MAKE) security-trust && $(MAKE) trust-manifest && $(MAKE) commercial-readiness && $(MAKE) public-sdk-packages-check && $(MAKE) iso-42001-readiness-check && $(MAKE) oss-diagnostics && $(MAKE) stabilization-readiness-check

# Stabilization readiness v1: bounded deterministic validators (metrics unit tests, DR scripts, evidence map, security program).
runtime-audit-metrics-check:
	@cd rust && cargo test -q metrics_endpoint

disaster-recovery-check:
	@cd python && python3 -m pip install -e '.[dev]' >/dev/null && python3 -m pytest tests/test_stabilization_scripts.py -q

evidence-map-check:
	@python3 scripts/evidence_map_check.py

security-program-check:
	@python3 scripts/security_program_check.py

stabilization-readiness-check:
	@$(MAKE) runtime-audit-metrics-check disaster-recovery-check evidence-map-check security-program-check
	@echo "stabilization-readiness-check: OK"

# Pilot execution and sales package diagnostics.
pilot-execution:
	@python3 scripts/pilot_execution_check.py

pilot-manifest:
	@python3 scripts/validate_pilot_manifest.py

# Revenue manifest + ROI + proposal tooling.
revenue-manifest:
	@python3 scripts/validate_revenue_manifest.py

revenue-roi:
	@python3 scripts/roi_calculator.py --input examples/revenue/sample-roi-input.json --json >/dev/null

revenue-proposal:
	@python3 scripts/generate_pilot_proposal.py --manifest docs/revenue/revenue-manifest.json --pilot-plan examples/pilot-execution/sample-pilot-plan.json >/dev/null

revenue-enablement:
	@python3 scripts/revenue_enablement_check.py

revenue-intelligence: revenue-intelligence-check
	@echo "revenue-intelligence: OK"

revenue-intelligence-manifest:
	@python3 scripts/validate_revenue_intelligence_manifest.py --json > .revenue-intelligence-manifest.json && echo "revenue-intelligence-manifest: OK"

customer-success-check: revenue-intelligence-check
	@python3 scripts/revenue_intelligence_check.py --json > .customer-success-check.json && echo "customer-success-check: OK"

revenue-intelligence-check: revenue-intelligence-manifest gate
	@python3 scripts/revenue_intelligence_check.py --json > .revenue-intelligence-check.json && echo "revenue-intelligence-check: OK"

go-to-market-check: pilot-execution pilot-manifest revenue-manifest revenue-roi revenue-proposal revenue-enablement gate
	@echo "go-to-market-check: OK"

# Community operations and contributor funnel checks.
community-operations-check:
	@python3 scripts/community_operations_check.py

contributor-funnel-check:
	@python3 scripts/community_operations_check.py --funnel-only

# Core launch narratives present.
launch-readiness:
	@python3 scripts/ecosystem_adoption_check.py --launch-only
	@echo "launch-readiness: OK"

# Launch, examples, community, and adoption report path checks.
ecosystem-adoption-check:
	@python3 scripts/ecosystem_adoption_check.py
	@echo "ecosystem-adoption-check: OK"

# Adoption kits, adoption documentation, and offline conformance samples.
adoption-kits-check:
	@python3 scripts/adoption_kits_check.py
	@echo "adoption-kits-check: OK"

# Reference implementation documentation, matrix, and operator guide checks.
reference-implementations-check:
	@python3 scripts/adoption_kits_check.py --reference-docs-only
	@echo "reference-implementations-check: OK"

# Developer integrations and SDK ecosystem documentation and examples.
developer-integrations-check:
	@python3 scripts/developer_integrations_check.py
	@echo "developer-integrations-check: OK"

public-sdk-packages-check:
	@python3 scripts/public_sdk_packages_check.py
	@echo "public-sdk-packages-check: OK"

# Strict doc links, developer integrations layout, TypeScript SDK validation,
# public SDK package labels, and audit report heading gate.
typescript-client-check:
	@cd typescript-sdk && npm install --no-audit --no-fund && npm run typecheck && npm run build && npm test
	@echo "typescript-client-check: OK"

sdk-ecosystem-check: docs-links-strict developer-integrations-check public-sdk-packages-check typescript-client-check gate
	@echo "sdk-ecosystem-check: OK"

# Customer operations manifest, diagnostics, checklist generator, and documentation gate.
customer-operations:
	@python3 scripts/customer_operations_check.py

customer-operations-manifest:
	@python3 scripts/validate_customer_operations_manifest.py

production-readiness-checklist:
	@python3 scripts/generate_production_readiness_checklist.py --manifest docs/operations/customer-operations-manifest.json >/dev/null && echo "production-readiness-checklist: OK"

production-operations-check: customer-operations customer-operations-manifest production-readiness-checklist gate
	@echo "production-operations-check: OK"

# Partner ecosystem manifest, diagnostics, and certification package generator.
partner-ecosystem:
	@python3 scripts/partner_ecosystem_check.py

partner-ecosystem-manifest:
	@python3 scripts/validate_partner_ecosystem_manifest.py

partner-certification-package:
	@python3 scripts/generate_partner_certification_package.py --manifest docs/partners/partner-ecosystem-manifest.json >/dev/null && echo "partner-certification-package: OK"

# Partner ecosystem aggregate (diagnostics + manifest + certification smoke + report gate).
partner-ecosystem-check: partner-ecosystem partner-ecosystem-manifest partner-certification-package gate
	@echo "partner-ecosystem-check: OK"

# Integration marketplace bundle (catalog JSON + docs/examples + report gate).
integration-marketplace-check:
	@python3 scripts/partner_ecosystem_check.py --integration-marketplace-only && $(MAKE) gate
	@echo "integration-marketplace-check: OK"

# Product analytics manifest validation and dashboard instrumentation diagnostics (stdlib).
product-analytics-check:
	@python3 scripts/validate_product_analytics_manifest.py
	@python3 scripts/product_analytics_check.py
	@echo "product-analytics-check: OK"

# Product analytics checks plus audit report heading gate.
growth-instrumentation-check: product-analytics-check gate
	@echo "growth-instrumentation-check: OK"

# EU AI Act mapping and regulatory evidence validators.
regulatory-manifest:
	@python3 scripts/validate_regulatory_evidence_manifest.py

ai-act-obligations:
	@python3 scripts/validate_ai_act_obligations.py

regulatory-evidence:
	@python3 scripts/regulatory_evidence_check.py

regulatory-export:
	@python3 scripts/generate_regulatory_evidence_export.py --manifest docs/regulatory/regulatory-evidence-manifest.json >/dev/null && echo "regulatory-export: OK"

regulatory-check: regulatory-evidence regulatory-manifest ai-act-obligations regulatory-export gate
	@echo "regulatory-check: OK"

# ISO/IEC 42001 readiness support (manifest + clause index; not certification).
iso-42001-manifest:
	@python3 scripts/validate_iso_42001_alignment_manifest.py

iso-42001-clause-index:
	@python3 scripts/validate_iso_42001_clause_index.py

iso-42001-readiness-check: iso-42001-manifest iso-42001-clause-index
	@python3 scripts/iso_42001_readiness_check.py
	@echo "iso-42001-readiness-check: OK"

# Runtime observability and operational intelligence.
observability:
	@python3 scripts/observability_check.py

observability-manifest:
	@python3 scripts/validate_observability_manifest.py

operational-snapshot:
	@python3 scripts/validate_operational_snapshot.py --input examples/observability/sample-operational-snapshot.json

operational-health-score:
	@python3 scripts/operational_health_score.py --input examples/observability/sample-operational-snapshot.json >/dev/null && echo "operational-health-score: OK"

operational-intelligence-report:
	@python3 scripts/generate_operational_intelligence_report.py --input examples/observability/sample-operational-snapshot.json >/dev/null && echo "operational-intelligence-report: OK"

observability-check: observability observability-manifest operational-snapshot operational-health-score operational-intelligence-report runtime-audit-metrics-check gate
	@echo "observability-check: OK"

# Runtime safety, guardrails, escalation, human oversight, and override readiness.
runtime-safety:
	@python3 scripts/runtime_safety_check.py

runtime-safety-manifest:
	@python3 scripts/validate_runtime_safety_manifest.py

runtime-safety-snapshot:
	@python3 scripts/validate_runtime_safety_snapshot.py --input examples/runtime-safety/sample-runtime-safety-snapshot.json

runtime-safety-score:
	@python3 scripts/runtime_safety_score.py --input examples/runtime-safety/sample-runtime-safety-snapshot.json >/dev/null && echo "runtime-safety-score: OK"

runtime-safety-report:
	@python3 scripts/generate_runtime_safety_report.py --input examples/runtime-safety/sample-runtime-safety-snapshot.json >/dev/null && echo "runtime-safety-report: OK"

runtime-safety-check: runtime-safety runtime-safety-manifest runtime-safety-snapshot runtime-safety-score runtime-safety-report gate
	@echo "runtime-safety-check: OK"

# Hosted platform readiness: manifest, snapshot, scoring, customer export, aggregate gate.
hosted-platform:
	@python3 scripts/hosted_platform_check.py

hosted-platform-manifest:
	@python3 scripts/validate_hosted_platform_manifest.py

hosted-readiness-snapshot:
	@python3 scripts/validate_hosted_readiness_snapshot.py --input examples/hosted-platform/sample-hosted-readiness-snapshot.json

hosted-readiness-score:
	@python3 scripts/hosted_readiness_score.py --input examples/hosted-platform/sample-hosted-readiness-snapshot.json >/dev/null && echo "hosted-readiness-score: OK"

hosted-readiness-export:
	@python3 scripts/generate_hosted_readiness_export.py --input examples/hosted-platform/sample-hosted-readiness-snapshot.json >/dev/null && echo "hosted-readiness-export: OK"

hosted-platform-check: hosted-platform hosted-platform-manifest hosted-readiness-snapshot hosted-readiness-score hosted-readiness-export gate
	@echo "hosted-platform-check: OK"

# Research artefacts, academic citation metadata, reproducibility bundle (stdlib validators; no network).
research-package-check:
	@python3 scripts/research_package_check.py && echo "research-package-check: OK"

academic-publication-check: research-package-check gate
	@echo "academic-publication-check: OK"

# Multi-tenant governance and enterprise RBAC (machine-readable bundle, docs, examples; stdlib validators).
multi-tenant:
	@python3 scripts/multi_tenant_check.py

multi-tenant-check: multi-tenant gate
	@echo "multi-tenant-check: OK"

tenant-isolation-check:
	@python3 scripts/multi_tenant_check.py --tenant-isolation-only
	@echo "tenant-isolation-check: OK"

# Validates hosted/production-readiness-checklist.json and docs/hosted/production-readiness.md only.
production-readiness-check:
	@python3 scripts/hosted_platform_check.py --production-readiness-only
	@echo "production-readiness-check: OK"

# GovBase hosted SaaS foundation on govbase.dev (multi-tenant contract, onboarding, billing boundary, monitoring, DR).
hosted-saas-readiness:
	@python3 scripts/hosted_saas_readiness_check.py

hosted-saas-readiness-check: hosted-saas-readiness hosted-platform-check
	@echo "hosted-saas-readiness-check: OK"

# AI Act conformity automation and regulatory workflows (machine-readable bundle, docs, examples; stdlib validators).
# Documents operator workflows for conformity assessment, technical documentation (Annex IV),
# risk management, post-market monitoring, and serious incident reporting. Does not change
# verdict semantics, Rust enforcement, or database migrations.
conformity-workflow-check:
	@python3 scripts/conformity_workflow_check.py && $(MAKE) gate && echo "conformity-workflow-check: OK"

regulatory-workflow-check:
	@python3 scripts/conformity_workflow_check.py --regulatory-workflow-only && echo "regulatory-workflow-check: OK"

# Registry JSON validation + documentation report gate (stdlib).
# Agent governance, delegation, and multi-agent control.
agent-governance:
	@python3 scripts/agent_governance_check.py

agent-governance-manifest:
	@python3 scripts/validate_agent_governance_manifest.py

agent-delegation-snapshot:
	@python3 scripts/validate_agent_delegation_snapshot.py --input examples/agent-governance/sample-agent-delegation-snapshot.json

agent-governance-score:
	@python3 scripts/agent_governance_score.py --input examples/agent-governance/sample-agent-delegation-snapshot.json >/dev/null && echo "agent-governance-score: OK"

agent-governance-report:
	@python3 scripts/generate_agent_governance_report.py --input examples/agent-governance/sample-agent-delegation-snapshot.json >/dev/null && echo "agent-governance-report: OK"

agent-governance-check: agent-governance agent-governance-manifest agent-delegation-snapshot agent-governance-score agent-governance-report gate
	@echo "agent-governance-check: OK"

# Autonomous and multi-agent governance (JSON bundle under autonomous/, docs, examples; stdlib check + report gate).
autonomous-governance-check:
	@python3 scripts/autonomous_governance_check.py && $(MAKE) gate

multi-agent-governance-check:
	@python3 scripts/autonomous_governance_check.py --multi-agent && $(MAKE) gate

# Registry validation and documentation report gate (stdlib).
registry-check:
	@python3 scripts/registry_check.py

registry-validation-check: registry-check gate
	@echo "registry-validation-check: OK"

# Marketplace manifest, extension package, diagnostics, and listing generator.
marketplace:
	@python3 scripts/marketplace_check.py

marketplace-manifest:
	@python3 scripts/validate_marketplace_manifest.py

extension-package:
	@python3 scripts/validate_extension_package.py --package examples/marketplace/sample-extension-package.json

marketplace-listing:
	@python3 scripts/generate_marketplace_listing.py --package examples/marketplace/sample-extension-package.json >/dev/null && echo "marketplace-listing: OK"

marketplace-check: marketplace marketplace-manifest extension-package marketplace-listing gate
	@echo "marketplace-check: OK"

# Model risk, evaluation, and assurance (stdlib validators + deterministic scoring).
model-risk:
	@python3 scripts/model_risk_check.py

model-risk-manifest:
	@python3 scripts/validate_model_risk_manifest.py

model-evaluation-snapshot:
	@python3 scripts/validate_model_evaluation_snapshot.py --input examples/model-risk/sample-model-evaluation-snapshot.json

model-risk-score:
	@python3 scripts/model_risk_score.py --input examples/model-risk/sample-model-evaluation-snapshot.json >/dev/null && echo "model-risk-score: OK"

model-assurance-report:
	@python3 scripts/generate_model_assurance_report.py --input examples/model-risk/sample-model-evaluation-snapshot.json >/dev/null && echo "model-assurance-report: OK"

model-risk-assurance-check: model-risk model-risk-manifest model-evaluation-snapshot model-risk-score model-assurance-report gate
	@echo "model-risk-assurance-check: OK"

# Public launch manifest, ecosystem standardization readiness snapshot, validators,
# readiness scoring, diagnostics, and deterministic Markdown report (stdlib; no network).
public-launch:
	@python3 scripts/public_launch_check.py && echo "public-launch: OK"

public-launch-manifest:
	@python3 scripts/validate_public_launch_manifest.py && echo "public-launch-manifest: OK"

standardization-readiness-snapshot:
	@python3 scripts/validate_standardization_readiness_snapshot.py --input examples/launch/sample-standardization-readiness-snapshot.json && echo "standardization-readiness-snapshot: OK"

public-launch-readiness-score:
	@python3 scripts/public_launch_readiness_score.py --input examples/launch/sample-standardization-readiness-snapshot.json >/dev/null && echo "public-launch-readiness-score: OK"

public-launch-report:
	@python3 scripts/generate_public_launch_report.py --input examples/launch/sample-standardization-readiness-snapshot.json >/dev/null && echo "public-launch-report: OK"

public-launch-check: public-launch public-launch-manifest standardization-readiness-snapshot public-launch-readiness-score public-launch-report gate
	@echo "public-launch-check: OK"

# Policy pack marketplace: catalog manifest and example packs.
policy-pack-check:
	@set -euo pipefail; \
	python3 scripts/validate_policy_pack.py examples/marketplace/eu-ai-act-basic; \
	python3 scripts/validate_policy_pack.py examples/marketplace/financial-services-ai; \
	python3 scripts/validate_policy_pack.py examples/marketplace/healthcare-ai; \
	python3 scripts/validate_policy_pack.py examples/marketplace/internal-model-risk; \
	python3 scripts/validate_policy_pack.py examples/marketplace/vendor-evaluation; \
	python3 scripts/validate_policy_pack.py examples/marketplace/vendor-risk; \
	echo "policy-pack-check: OK"

# Customer analytics manifest, health sample validators, scoring, EBR, and diagnostics.
customer-analytics:
	@python3 scripts/customer_analytics_check.py

customer-analytics-manifest:
	@python3 scripts/validate_customer_analytics_manifest.py

customer-health-score:
	@python3 scripts/customer_health_score.py --input examples/customer-analytics/sample-customer-health.json >/dev/null && echo "customer-health-score: OK"

executive-business-review:
	@python3 scripts/generate_executive_business_review.py --input examples/customer-analytics/sample-customer-health.json >/dev/null && echo "executive-business-review: OK"

customer-analytics-check: customer-analytics customer-analytics-manifest customer-health-score executive-business-review gate
	@echo "customer-analytics-check: OK"

# Developer integrations manifest, automation pack, diagnostics, and summary.
developer-integrations:
	@python3 scripts/developer_integrations_check.py && echo "developer-integrations: OK"

developer-integrations-manifest:
	@python3 scripts/validate_developer_integrations_manifest.py && echo "developer-integrations-manifest: OK"

automation-pack:
	@python3 scripts/validate_automation_pack.py --pack examples/integrations/sample-automation-pack.json && echo "automation-pack: OK"

automation-pack-summary:
	@python3 scripts/generate_automation_pack_summary.py --pack examples/integrations/sample-automation-pack.json >/dev/null && echo "automation-pack-summary: OK"

policy-intelligence:
	@python3 scripts/policy_intelligence_check.py

policy-intelligence-manifest:
	@python3 scripts/validate_policy_intelligence_manifest.py

governance-control-snapshot:
	@python3 scripts/validate_governance_control_snapshot.py

policy-coverage-score:
	@python3 scripts/policy_coverage_score.py --input examples/policy-intelligence/sample-governance-control-snapshot.json --json >/dev/null && echo "policy-coverage-score: OK"

governance-control-report:
	@python3 scripts/generate_governance_control_report.py --input examples/policy-intelligence/sample-governance-control-snapshot.json >/dev/null && echo "governance-control-report: OK"

policy-intelligence-check: policy-intelligence policy-intelligence-manifest governance-control-snapshot policy-coverage-score governance-control-report gate
	@echo "policy-intelligence-check: OK"

# Autonomous governance posture aggregate (manifest, snapshot, scoring, report, diagnostics).
control-plane:
	@python3 scripts/governance_posture_aggregate_check.py

# Enterprise governance machine-readable artefacts under control-plane/ (roles, delegation, escalation, ownership).
control-plane-check:
	@python3 scripts/control_plane_check.py

enterprise-governance-check: control-plane-check gate
	@echo "enterprise-governance-check: OK"

control-plane-manifest:
	@python3 scripts/validate_control_plane_manifest.py

governance-posture-snapshot:
	@python3 scripts/validate_governance_posture_snapshot.py --input examples/control-plane/sample-governance-posture-snapshot.json

governance-posture-score:
	@python3 scripts/governance_posture_score.py --input examples/control-plane/sample-governance-posture-snapshot.json >/dev/null && echo "governance-posture-score: OK"

control-plane-report:
	@python3 scripts/generate_control_plane_report.py --input examples/control-plane/sample-governance-posture-snapshot.json >/dev/null && echo "control-plane-report: OK"

# Enterprise governance posture aggregate (manifest, snapshot, scoring, report, gate).
governance-posture-check: control-plane control-plane-manifest governance-posture-snapshot governance-posture-score control-plane-report gate
	@echo "governance-posture-check: OK"

# Release operations (manifest, validators, notes generator, readiness JSON; stdlib).
release-manifest:
	@python3 scripts/validate_release_manifest.py

validate-changelog:
	@python3 scripts/validate_changelog.py

GOVAI_GENERATE_RELEASE_NOTES_VERSION ?= 1.0.0
generate-release-notes:
	@python3 scripts/generate_release_notes.py --version $(GOVAI_GENERATE_RELEASE_NOTES_VERSION) --out examples/releases/sample-generated-release-notes-1.0.0.md && echo "generate-release-notes: OK"

release-readiness-report:
	@python3 scripts/release_readiness_report.py --json >/dev/null && echo "release-readiness-report: OK"

release-operations-check:
	@python3 scripts/release_operations_check.py

release-readiness-check: release-operations-check release-manifest validate-changelog release-readiness-report docs-links-strict gate
	@echo "release-readiness-check: OK"

# GovAI Cursor plugin (manifest, rules, skills, local MCP bridge)
cursor-plugin-validate:
	@python3 scripts/validate_cursor_plugin.py

cursor-plugin-smoke:
	@python3 scripts/smoke_cursor_plugin.py

cursor-plugin-check: cursor-plugin-validate cursor-plugin-smoke
	@echo "cursor-plugin-check: OK"

# Optional: read-only probe against operator-configured GOVAI_AUDIT_BASE_URL (Platform/self-host). Core does not start a server.
local-demo:
	@python3 scripts/run_local_demo.py

local-demo-curl:
	@bash examples/local-demo/curl-health-ready.sh

# Fail-closed BLOCKED demo: requires running audit API + Postgres (e.g. docker compose up), GOVAI_API_KEY matching compose.
fail-closed-demo:
	@python3 scripts/run_fail_closed_demo.py

engineering_loc:
	@python3 scripts/engineering_loc.py

# Portable offline digest helper (no HTTP server).
audit:
	cd rust && cargo run --bin $(AIGOV_AUDIT_BIN) --locked

build-audit:
	cd rust && cargo build --locked --bin aigov_audit

# Run the ledger-authoritative HTTP runtime (bind: AIGOV_BIND, default 127.0.0.1:8088).
run-audit: build-audit
	cd rust && cargo run --bin aigov_audit --locked

audit_bg audit_stop audit_restart audit_logs:
	@echo "$@: GovAI Core does not manage a hosted audit HTTP service lifecycle."
	@echo "Run the GovAI Platform repository for SaaS runtime orchestration, or configure GOVAI_AUDIT_BASE_URL to your operator runtime."
	@exit 2
require_audit_url:
	@if [ -z "$${GOVAI_AUDIT_BASE_URL:-}" ]; then \
		echo "GOVAI_AUDIT_BASE_URL is required (GovAI Core does not start a local audit server)."; \
		echo "Point it at GovAI Platform or your self-host runtime, or use offline targets: governance-standards-check, scripts/ci_portable_artifact_bundle.py"; \
		exit 2; \
	fi

status: require_audit_url
	curl -sS "$(GOVAI_AUDIT_BASE_URL)/status" ; echo

verify: require_audit_url
	curl -sS "$(GOVAI_AUDIT_BASE_URL)/verify" ; echo

verify_log: require_audit_url
	curl -sS "$(GOVAI_AUDIT_BASE_URL)/verify-log" ; echo

# ================================
# Core
# ================================

run: require_audit_url
	cd python && . .venv/bin/activate && \
	GOVAI_AUDIT_BASE_URL=$${GOVAI_AUDIT_BASE_URL} GOVAI_API_KEY=$${GOVAI_API_KEY:-ci-test-api-key} GOVAI_PROJECT=$${GOVAI_PROJECT:-github-actions} RUN_ID=$(RUN_ID) python -m aigov_py.pipeline_train

require_run:
	@if [ -z "$(RUN_ID)" ]; then \
		echo "RUN_ID is required"; \
		exit 2; \
	fi

check_audit:
	@echo "check_audit: removed in GovAI Core (no GET /ready polling or localhost orchestration)."
	@echo "Use require_audit_url + operator runtime, or offline portable CI: python3 scripts/ci_portable_artifact_bundle.py"
	@exit 2

ensure_dirs:
	@mkdir -p docs/reports docs/audit docs/audit_meta docs/packs docs/evidence docs/policy

ensure_reports_dir:
	@mkdir -p docs/reports

new_run:
	@python3 -c 'import uuid; print(str(uuid.uuid4()))'

report_new:
	@$(MAKE) new_run

# ================================
# Evidence
# ================================

ensure_evidence: require_run ensure_dirs
	@set -euo pipefail; \
	if [ ! -f "docs/evidence/$(RUN_ID).json" ] && [ "$(AIGOV_MODE)" = "prod" ]; then \
		echo "ERROR: missing evidence in prod mode"; \
		exit 2; \
	fi; \
	cd python && . .venv/bin/activate && \
	if [ "$${AIGOV_COMPLIANCE_FETCH_STRICT:-}" = "1" ]; then \
		echo "ensure_evidence: strict fetch (no ci_fallback) RUN_ID=$(RUN_ID)"; \
		AIGOV_MODE=$(AIGOV_MODE) python -m aigov_py.fetch_bundle_from_govai $(RUN_ID); \
	else \
		AIGOV_MODE=$(AIGOV_MODE) python -m aigov_py.fetch_bundle_from_govai $(RUN_ID) || \
		AIGOV_MODE=$(AIGOV_MODE) python -m aigov_py.ci_fallback $(RUN_ID); \
	fi

# ================================
# Report flow
# ================================

report_template: require_run ensure_reports_dir
	@echo "run_id=$(RUN_ID)" > docs/reports/$(RUN_ID).md
	@echo "bundle_sha256=" >> docs/reports/$(RUN_ID).md
	@echo "policy_version=" >> docs/reports/$(RUN_ID).md
	@echo "" >> docs/reports/$(RUN_ID).md
	@echo "# Audit report for run \`$(RUN_ID)\`" >> docs/reports/$(RUN_ID).md
	@echo "" >> docs/reports/$(RUN_ID).md
	@echo "saved docs/reports/$(RUN_ID).md"

report_init: require_run ensure_reports_dir
	cd python && . .venv/bin/activate && \
	AIGOV_MODE=$(AIGOV_MODE) python -m aigov_py.report_init $(RUN_ID)

report_fill: require_run ensure_reports_dir
	cd python && . .venv/bin/activate && \
	AIGOV_MODE=$(AIGOV_MODE) python -m aigov_py.report_fill $(RUN_ID)

bundle: require_run ensure_dirs
	cd python && . .venv/bin/activate && \
	AIGOV_MODE=$(AIGOV_MODE) python -m aigov_py.export_bundle $(RUN_ID)

verify_cli: require_run
	cd python && . .venv/bin/activate && \
	AIGOV_MODE=$(AIGOV_MODE) python -m aigov_py.verify $(RUN_ID)

evidence_pack: require_run ensure_dirs
	cd python && . .venv/bin/activate && \
	AIGOV_MODE=$(AIGOV_MODE) RUN_ID=$(RUN_ID) python -m aigov_py.evidence_pack

audit_close: require_run
	cd python && . .venv/bin/activate && \
	AIGOV_MODE=$(AIGOV_MODE) python -m aigov_py.audit_close $(RUN_ID)

report_prepare: require_run
	@echo "Preparing report for RUN_ID=$(RUN_ID) (AIGOV_MODE=$(AIGOV_MODE))"
	$(MAKE) ensure_evidence RUN_ID=$(RUN_ID)
	cd python && . .venv/bin/activate && \
		RUN_ID=$(RUN_ID) AIGOV_MODE=$(AIGOV_MODE) python -m aigov_py.report
	$(MAKE) export_bundle RUN_ID=$(RUN_ID)
	$(MAKE) verify_cli RUN_ID=$(RUN_ID)

report_prepare_new:
	@set -euo pipefail; \
	RUN_ID="$$(python3 -c 'import uuid; print(str(uuid.uuid4()))')"; \
	echo "$$RUN_ID"; \
	$(MAKE) report_prepare RUN_ID="$$RUN_ID"

# ================================
# Supabase ingest
# ================================

db_ingest: require_run
	cd python && . .venv/bin/activate && \
	AIGOV_MODE=$(AIGOV_MODE) python -m aigov_py.ingest_run $(RUN_ID)

# ================================
# Demo
# ================================
# demo: end to end run that generates artifacts and ingests a row to Supabase
# demo_new: same but generates RUN_ID automatically and prints it for dashboard usage

demo: require_run require_audit_url
	@set -euo pipefail; \
	echo "DEMO: RUN_ID=$(RUN_ID) AIGOV_MODE=$(AIGOV_MODE)"; \
	$(MAKE) run RUN_ID="$(RUN_ID)"; \
	$(MAKE) approve RUN_ID="$(RUN_ID)"; \
	$(MAKE) promote RUN_ID="$(RUN_ID)"; \
	$(MAKE) report_prepare RUN_ID="$(RUN_ID)"; \
	$(MAKE) db_ingest RUN_ID="$(RUN_ID)"; \
	echo "OK: demo completed RUN_ID=$(RUN_ID)"; \
	echo "Dashboard: /runs/$(RUN_ID)"

demo_new: require_audit_url
	@set -euo pipefail; \
	RUN_ID="$$(python3 -c 'import uuid; print(str(uuid.uuid4()))')"; \
	echo "DEMO: generated RUN_ID=$$RUN_ID AIGOV_MODE=$(AIGOV_MODE)"; \
	$(MAKE) run RUN_ID="$$RUN_ID"; \
	$(MAKE) approve RUN_ID="$$RUN_ID"; \
	$(MAKE) promote RUN_ID="$$RUN_ID"; \
	$(MAKE) report_prepare RUN_ID="$$RUN_ID"; \
	$(MAKE) db_ingest RUN_ID="$$RUN_ID"; \
	echo "OK: demo completed RUN_ID=$$RUN_ID"; \
	echo "Dashboard: /runs/$$RUN_ID"

# Train → approve → promote → report_prepare (evidence + report + bundle + verify_cli) → compliance summary (HTTP)
flow_full: require_run require_audit_url
	@set -euo pipefail; \
	echo "flow_full: RUN_ID=$(RUN_ID) AIGOV_MODE=$(AIGOV_MODE)"; \
	$(MAKE) run RUN_ID="$(RUN_ID)"; \
	$(MAKE) approve RUN_ID="$(RUN_ID)"; \
	$(MAKE) promote RUN_ID="$(RUN_ID)"; \
	$(MAKE) report_prepare RUN_ID="$(RUN_ID)"; \
	cd python && . .venv/bin/activate && \
		RUN_ID="$(RUN_ID)" AIGOV_MODE="$(AIGOV_MODE)" python -m aigov_py.ai_discovery_completed; \
	echo "GET $(GOVAI_AUDIT_BASE_URL)/compliance-summary?run_id=$(RUN_ID)"; \
	curl -fsS "$(GOVAI_AUDIT_BASE_URL)/compliance-summary?run_id=$(RUN_ID)"; echo

flow: flow_full

# Thin wrappers around Python scripts (core flow glue)
approve: require_run require_audit_url
	cd python && . .venv/bin/activate && \
		GOVAI_AUDIT_BASE_URL=$${GOVAI_AUDIT_BASE_URL} GOVAI_API_KEY=$${GOVAI_API_KEY:-ci-test-api-key} GOVAI_PROJECT=$${GOVAI_PROJECT:-github-actions} RUN_ID=$(RUN_ID) AIGOV_MODE=$(AIGOV_MODE) python -m aigov_py.approve

promote: require_run require_audit_url
	cd python && . .venv/bin/activate && \
		GOVAI_AUDIT_BASE_URL=$${GOVAI_AUDIT_BASE_URL} GOVAI_API_KEY=$${GOVAI_API_KEY:-ci-test-api-key} GOVAI_PROJECT=$${GOVAI_PROJECT:-github-actions} RUN_ID=$(RUN_ID) AIGOV_MODE=$(AIGOV_MODE) python -m aigov_py.promote

export_bundle: require_run ensure_dirs
	cd python && . .venv/bin/activate && \
		AIGOV_MODE=$(AIGOV_MODE) python -m aigov_py.export_bundle $(RUN_ID)

# ================================
# PR helpers
# ================================

pr_report:
	@set -euo pipefail; \
	RUN_ID="$$(python3 -c 'import uuid; print(str(uuid.uuid4()))')"; \
	echo "Generated RUN_ID=$$RUN_ID"; \
	$(MAKE) report_prepare RUN_ID="$$RUN_ID"

pr_report_commit: FORCE
	@set -euo pipefail; \
	BRANCH="$$(git rev-parse --abbrev-ref HEAD)"; \
	if [ "$$BRANCH" = "main" ]; then \
		echo "ERROR: do not run on main branch"; \
		exit 2; \
	fi; \
	if ! git diff --quiet || ! git diff --cached --quiet; then \
		echo "ERROR: working tree not clean. Commit or stash first."; \
		exit 2; \
	fi; \
	RUN_ID="$$(python3 -c 'import uuid; print(str(uuid.uuid4()))')"; \
	echo "Generated RUN_ID=$$RUN_ID"; \
	$(MAKE) report_prepare RUN_ID="$$RUN_ID"; \
	git add "docs/reports/$$RUN_ID.md"; \
	if git diff --cached --quiet; then \
		echo "ERROR: nothing staged (report not generated?)"; \
		exit 2; \
	fi; \
	git commit -m "docs: add audit report ($$RUN_ID)"; \
	git push

# Evidence quality, provenance snapshots, scoring, and dataset governance reports.
evidence-quality:
	@python3 scripts/evidence_quality_check.py

evidence-quality-manifest:
	@python3 scripts/validate_evidence_quality_manifest.py

dataset-provenance-snapshot:
	@python3 scripts/validate_dataset_provenance_snapshot.py

evidence-quality-score:
	@python3 scripts/evidence_quality_score.py --input examples/evidence-quality/sample-dataset-provenance-snapshot.json >/dev/null && echo "evidence-quality-score: OK"

dataset-governance-report:
	@python3 scripts/generate_dataset_governance_report.py --input examples/evidence-quality/sample-dataset-provenance-snapshot.json >/dev/null && echo "dataset-governance-report: OK"

# Runtime SDK layout and imports.
runtime-sdk-check:
	@python3 scripts/runtime_sdk_check.py

runtime-sdk-platform-check: runtime-sdk-check gate
	@echo "runtime-sdk-platform-check: OK"

evidence-quality-check: evidence-quality evidence-quality-manifest dataset-provenance-snapshot evidence-quality-score dataset-governance-report gate
	@echo "evidence-quality-check: OK"
developer-integrations-platform-check: developer-integrations-check
	@echo "developer-integrations-platform-check: OK"

regulatory-evidence-check: regulatory-evidence regulatory-manifest ai-act-obligations regulatory-export gate
	@echo "regulatory-evidence-check: OK"









manuscript-evidence-check:
	@GOVAI_EMPIRICAL_QUICK=1 python3 scripts/manuscript_evidence_runner.py && echo "manuscript-evidence-check: OK"
