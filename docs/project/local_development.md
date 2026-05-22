# Local development

Concise path from clone to a working audit service, documentation gates, and tests. For product semantics, stay with the canonical guides linked at the end.

## Prerequisites

- Git, Docker with Compose v2, Python **3.10+**, Rust toolchain (`cargo`).
- Ports **8088** (audit HTTP) and **5432** (Postgres) available locally.

## 1. Clone

```bash
git clone https://github.com/MonikaDvorackova/aigov-compliance-engine.git
cd aigov-compliance-engine
```

## 2. Python tooling (venv + editable install)

The CLI and tests live under `python/`. Create a venv **inside** `python/` (matches `Makefile` targets that run `cd python && . .venv/bin/activate`):

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
cd ..
```

If `pytest` fails at import time with `ModuleNotFoundError` (for example `nacl`), install the editable package in that venv as above; **`PyNaCl`** is declared in `python/pyproject.toml`.

## 3. Audit service via Docker Compose

From the **repository root**:

```bash
docker compose up -d --build
```

Health (liveness; available only after the service has bound HTTP):

```bash
curl -fsS http://127.0.0.1:8088/health
```

Operational readiness (Postgres + migrations + writable ledger expectations used by the service):

```bash
curl -fsS http://127.0.0.1:8088/ready
```

Root `docker-compose.yml` sets **`GOVAI_API_KEYS`** for the container (see file for the dev value). Use the same bearer token when calling authenticated routes from your shell.

## 4. Optional root `.env`

`Makefile` does `-include .env`. Copy **`.env.example`** to **`.env`** for local overrides only; never commit secrets.

## 5. Documentation report gate

From the repository root (uses system `python3` and `scripts/gate_reports.py`):

```bash
python3 scripts/gate_reports.py
make gate
```

## 5b. OSS health, metrics, and local link checks (stdlib scripts)

These targets use **stdlib-only** Python under `scripts/` (no network, no writes):

```bash
make oss-health                      # required contributor/OSS files exist (exits 1 if missing)
make oss-metrics                     # Markdown / examples / test counts (Markdown table to stdout)
make docs-links                      # README + docs/**/*.md relative links (warn-only; exits 0 if broken)
make docs-links-strict               # same as docs-links with --strict (exits 1 on broken local links)
make security-trust                  # structured security/trust diagnostics (deterministic JSON: add --json)
make trust-manifest                  # validate docs/trust/trust-manifest.json (deterministic JSON: add --json)
make trust-chain-check               # validate trust/*.json + examples/trust (stdlib; add --json)
make immutable-trust-check           # trust-chain-check + gate
make commercial-readiness            # commercial readiness diagnostics
make commercial-readiness-check      # commercial-readiness + gate
make oss-diagnostics                 # aggregated JSON: layout, health, strict links, docs/reports vs origin/staging when ref exists
make enterprise-readiness-check      # security-trust + trust-manifest + commercial-readiness + oss-diagnostics
make pilot-execution                 # pilot/sales package path diagnostics (human table; add --json on the script)
make pilot-manifest                  # validate docs/pilots/pilot-manifest.json
make pilot-check                     # pilot-execution + pilot-manifest + gate
make customer-operations             # customer operations path diagnostics
make customer-operations-manifest    # validate docs/operations/customer-operations-manifest.json
make production-readiness-checklist  # runs checklist generator
make customer-operations-check       # customer-operations + customer-operations-manifest + production-readiness-checklist + gate
make partner-ecosystem               # partner ecosystem path diagnostics
make partner-ecosystem-manifest      # validate docs/partners/partner-ecosystem-manifest.json
make partner-certification-package   # certification package generator smoke
make partner-ecosystem-check         # partner-ecosystem + partner-ecosystem-manifest + partner-certification-package + gate
make regulatory-evidence             # regulatory diagnostics
make regulatory-manifest             # validate docs/regulatory/regulatory-evidence-manifest.json
make ai-act-obligations              # validate docs/regulatory/ai-act-obligations.json
make regulatory-export               # Markdown export smoke
make regulatory-check                # regulatory-evidence + regulatory-manifest + ai-act-obligations + regulatory-export + gate
make observability                   # aggregated observability diagnostics (human table; add --json on the script)
make observability-manifest          # validate docs/observability/observability-manifest.json
make operational-snapshot            # validate examples/observability/sample-operational-snapshot.json
make operational-health-score        # deterministic JSON: ok, health_score, readiness_score, evidence_score, diagnostics_score, risk_level, findings
make operational-intelligence-report # Markdown report generator smoke (discards stdout; verifies generator succeeds)
make observability-check             # observability + observability-manifest + operational-snapshot + operational-health-score + operational-intelligence-report + gate

make runtime-safety                  # aggregated runtime safety diagnostics (human table; add --json on the script)
make runtime-safety-manifest         # validate docs/runtime-safety/runtime-safety-manifest.json
make runtime-safety-snapshot         # validate examples/runtime-safety/sample-runtime-safety-snapshot.json
make runtime-safety-score            # deterministic JSON: ok, runtime_safety_score, subscores, risk_level, findings, recommendations
make runtime-safety-report           # Markdown runtime safety report generator smoke
make runtime-safety-check            # runtime-safety + runtime-safety-manifest + runtime-safety-snapshot + runtime-safety-score + runtime-safety-report + gate

make hosted-platform                 # hosted platform readiness diagnostics (human table; add --json on the script)
make hosted-platform-manifest        # validate docs/hosted-platform/hosted-platform-manifest.json
make hosted-readiness-snapshot       # validate examples/hosted-platform/sample-hosted-readiness-snapshot.json
make hosted-readiness-score          # deterministic hosted readiness JSON (sample path)
make hosted-readiness-export         # customer-facing Markdown export smoke
make hosted-platform-check           # hosted-platform + manifest + snapshot + score + export + gate

make evidence-quality                # evidence quality diagnostics (stdlib; add --json on the script)
make evidence-quality-manifest       # validate docs/evidence-quality/evidence-quality-manifest.json
make dataset-provenance-snapshot     # validate examples/evidence-quality/sample-dataset-provenance-snapshot.json
make evidence-quality-score          # deterministic JSON: ok, evidence_quality_score, subscores, maturity_level, findings, recommendations
make dataset-governance-report       # Markdown dataset governance report generator smoke
make evidence-quality-check          # evidence-quality + manifest + snapshot + score + report + gate

make hosted-platform                 # hosted platform readiness diagnostics (human table; add --json on the script)
make hosted-platform-manifest        # validate docs/hosted-platform/hosted-platform-manifest.json
make hosted-readiness-snapshot       # validate examples/hosted-platform/sample-hosted-readiness-snapshot.json
make hosted-readiness-score          # deterministic hosted readiness JSON (sample path)
make hosted-readiness-export         # customer-facing Markdown export smoke
make hosted-platform-check           # hosted-platform + manifest + snapshot + score + export + gate
make model-risk                      # model risk diagnostics (stdlib; add --json on the script)
make model-risk-manifest             # validate docs/model-risk/model-risk-manifest.json
make model-evaluation-snapshot       # validate examples/model-risk/sample-model-evaluation-snapshot.json
make model-risk-score                # deterministic model risk JSON (sample path)
make model-assurance-report          # Markdown assurance report generator smoke
make model-risk-assurance-check      # model-risk + validators + score + report + gate

make agent-governance                # agent governance diagnostics (human table; add --json on the script)
make agent-governance-manifest       # validate docs/agent-governance/agent-governance-manifest.json
make agent-delegation-snapshot       # validate examples/agent-governance/sample-agent-delegation-snapshot.json
make agent-governance-score          # deterministic JSON: ok, agent_governance_score, sub-scores, risk_level, findings, recommendations
make agent-governance-report         # Markdown governance report generator smoke
make agent-governance-check          # agent-governance + agent-governance-manifest + agent-delegation-snapshot + agent-governance-score + agent-governance-report + gate
make public-launch                  # public launch and ecosystem standardization diagnostics (stdlib)
make public-launch-manifest         # validate docs/launch/public-launch-manifest.json
make standardization-readiness-snapshot  # validate examples/launch/sample-standardization-readiness-snapshot.json
make public-launch-readiness-score  # deterministic readiness JSON scoring
make public-launch-report           # deterministic Markdown report generation
make public-launch-check            # public-launch + manifest + snapshot + score + report + gate
make marketplace                     # marketplace path diagnostics
make marketplace-manifest            # validate docs/marketplace/marketplace-manifest.json
make extension-package               # validate examples/marketplace/sample-extension-package.json
make marketplace-listing             # deterministic Markdown listing smoke
make marketplace-check               # marketplace + marketplace-manifest + extension-package + marketplace-listing + gate
make customer-analytics              # customer analytics diagnostics
make customer-analytics-manifest     # validate docs/analytics/customer-analytics-manifest.json
make customer-health-score           # smoke: deterministic JSON scoring for sample health input
make executive-business-review       # smoke: deterministic EBR Markdown from sample health input
make customer-analytics-check        # customer-analytics + customer-analytics-manifest + customer-health-score + executive-business-review + gate
make policy-intelligence             # policy intelligence path diagnostics (human table; add --json on the script)
make policy-intelligence-manifest    # validate docs/policy-intelligence/policy-intelligence-manifest.json
make governance-control-snapshot     # validate examples/policy-intelligence/sample-governance-control-snapshot.json
make policy-coverage-score           # smoke: deterministic JSON scoring for sample governance snapshot
make governance-control-report       # smoke: deterministic governance Markdown from sample snapshot
make policy-intelligence-check       # policy-intelligence + policy-intelligence-manifest + governance-control-snapshot + policy-coverage-score + governance-control-report + gate
make control-plane                   # control-plane diagnostics (stdlib)
make control-plane-manifest          # validate docs/control-plane/control-plane-manifest.json
make governance-posture-snapshot     # validate examples/control-plane/sample-governance-posture-snapshot.json
make governance-posture-score        # deterministic JSON scoring for sample posture snapshot
make control-plane-report            # deterministic Markdown report from sample posture snapshot
make governance-posture-check                   # control-plane + manifest + snapshot + score + report + gate
make developer-integrations          # developer integrations diagnostics
make developer-integrations-manifest # validate docs/integrations/developer-integrations-manifest.json
make automation-pack                 # validate examples/integrations/sample-automation-pack.json
make automation-pack-summary         # Markdown summary from sample automation pack
make developer-integrations-platform-check # developer-integrations + developer-integrations-manifest + automation-pack + automation-pack-summary + gate
make release-manifest                # validate docs/releases/release-manifest.json
make validate-changelog              # Keep a Changelog gate for CHANGELOG.md
make generate-release-notes          # writes sample release notes
make release-readiness-report        # aggregated release readiness
make release-readiness-check         # release readiness aggregate gate
```

**Machine-readable JSON (automation / CI mirrors):**

```bash
python3 scripts/repo_health_check.py --json
python3 scripts/security_trust_check.py --json
python3 scripts/validate_trust_manifest.py --json
python3 scripts/trust_chain_check.py --json
python3 scripts/pilot_execution_check.py --json
python3 scripts/validate_pilot_manifest.py --json
python3 scripts/customer_operations_check.py --json
python3 scripts/validate_customer_operations_manifest.py --json
python3 scripts/partner_ecosystem_check.py --json
python3 scripts/validate_partner_ecosystem_manifest.py --json
python3 scripts/generate_partner_certification_package.py --manifest docs/partners/partner-ecosystem-manifest.json
python3 scripts/regulatory_evidence_check.py --json
python3 scripts/validate_regulatory_evidence_manifest.py --json
python3 scripts/validate_ai_act_obligations.py --json
python3 scripts/generate_regulatory_evidence_export.py --manifest docs/regulatory/regulatory-evidence-manifest.json
python3 scripts/observability_check.py --json
python3 scripts/validate_observability_manifest.py --json
python3 scripts/validate_operational_snapshot.py --input examples/observability/sample-operational-snapshot.json --json
python3 scripts/operational_health_score.py --input examples/observability/sample-operational-snapshot.json
python3 scripts/generate_operational_intelligence_report.py --input examples/observability/sample-operational-snapshot.json
python3 scripts/runtime_safety_check.py --json
python3 scripts/validate_runtime_safety_manifest.py --json
python3 scripts/validate_runtime_safety_snapshot.py --input examples/runtime-safety/sample-runtime-safety-snapshot.json --json
python3 scripts/runtime_safety_score.py --input examples/runtime-safety/sample-runtime-safety-snapshot.json
python3 scripts/generate_runtime_safety_report.py --input examples/runtime-safety/sample-runtime-safety-snapshot.json
python3 scripts/hosted_platform_check.py --json
python3 scripts/validate_hosted_platform_manifest.py --json
python3 scripts/validate_hosted_readiness_snapshot.py --input examples/hosted-platform/sample-hosted-readiness-snapshot.json --json
python3 scripts/hosted_readiness_score.py --input examples/hosted-platform/sample-hosted-readiness-snapshot.json --json
python3 scripts/generate_hosted_readiness_export.py --input examples/hosted-platform/sample-hosted-readiness-snapshot.json

python3 scripts/agent_governance_check.py --json
python3 scripts/validate_agent_governance_manifest.py --json
python3 scripts/validate_agent_delegation_snapshot.py --input examples/agent-governance/sample-agent-delegation-snapshot.json --json
python3 scripts/agent_governance_score.py --input examples/agent-governance/sample-agent-delegation-snapshot.json --json
python3 scripts/generate_agent_governance_report.py --input examples/agent-governance/sample-agent-delegation-snapshot.json
python3 scripts/marketplace_check.py --json
python3 scripts/validate_marketplace_manifest.py --json
python3 scripts/validate_extension_package.py --json --package examples/marketplace/sample-extension-package.json
python3 scripts/generate_marketplace_listing.py --package examples/marketplace/sample-extension-package.json
python3 scripts/validate_marketplace_manifest.py --json --manifest marketplace/manifest.json
python3 scripts/validate_policy_pack.py --json examples/marketplace/eu-ai-act-basic
python3 scripts/validate_policy_pack.py --json examples/marketplace/internal-model-risk
python3 scripts/validate_policy_pack.py --json examples/marketplace/vendor-evaluation
python3 scripts/customer_analytics_check.py --json
python3 scripts/validate_customer_analytics_manifest.py --json
python3 scripts/customer_health_score.py --input examples/customer-analytics/sample-customer-health.json
python3 scripts/generate_executive_business_review.py --input examples/customer-analytics/sample-customer-health.json
python3 scripts/evidence_quality_check.py --json
python3 scripts/validate_evidence_quality_manifest.py --json
python3 scripts/validate_dataset_provenance_snapshot.py --json
python3 scripts/evidence_quality_score.py --input examples/evidence-quality/sample-dataset-provenance-snapshot.json
python3 scripts/generate_dataset_governance_report.py --input examples/evidence-quality/sample-dataset-provenance-snapshot.json
python3 scripts/policy_intelligence_check.py --json
python3 scripts/validate_policy_intelligence_manifest.py --json
python3 scripts/validate_governance_control_snapshot.py --json
python3 scripts/policy_coverage_score.py --input examples/policy-intelligence/sample-governance-control-snapshot.json --json
python3 scripts/generate_governance_control_report.py --input examples/policy-intelligence/sample-governance-control-snapshot.json
python3 scripts/control_plane_check.py --json
python3 scripts/governance_posture_aggregate_check.py --json
python3 scripts/validate_control_plane_manifest.py --json
python3 scripts/validate_governance_posture_snapshot.py --json --input examples/control-plane/sample-governance-posture-snapshot.json
python3 scripts/governance_posture_score.py --input examples/control-plane/sample-governance-posture-snapshot.json
python3 scripts/generate_control_plane_report.py --input examples/control-plane/sample-governance-posture-snapshot.json
python3 scripts/developer_integrations_check.py --json
python3 scripts/validate_developer_integrations_manifest.py --json
python3 scripts/validate_automation_pack.py --json --pack examples/integrations/sample-automation-pack.json
python3 scripts/generate_automation_pack_summary.py --pack examples/integrations/sample-automation-pack.json
python3 scripts/validate_release_manifest.py --json
python3 scripts/validate_changelog.py --json
python3 scripts/release_readiness_report.py --json
python3 scripts/validate_docs_links.py --strict --json
python3 scripts/oss_diagnostics.py --json
```

CI (`.github/workflows/oss-developer-experience.yml`) uploads structured diagnostics as the `oss-check-json` artifact after `make enterprise-readiness-check`. Browse the catalog interactively:

```artifacts
catalog: ci
```

**Enterprise security review example (no audit service):** **`bash examples/security-review/run-security-review-check.sh`** (from repo root).

**Fail-closed demo (requires running audit stack + `python/.venv` with `govai`):**

```bash
export GOVAI_AUDIT_BASE_URL=http://127.0.0.1:8088
export GOVAI_API_KEY=test-key   # must match root docker-compose.yml
make fail-closed-demo            # scripts/run_fail_closed_demo.py — BLOCKED contract, JSON on stdout
```

Read-only vs fail-closed semantics and exit codes: **`examples/local-demo/CONTRACT.md`**. Public docs preview: run the **`dashboard/`** dev server (`cd dashboard && npm ci && npm run dev`) and open **`/docs`** / **`/help`** (content is read from **`../docs/`** at build/runtime).

### Local audit read-only demo (optional)

With the audit API already listening (for example after **`docker compose up -d --build`**):

```bash
make local-demo       # python3 scripts/run_local_demo.py — GET /health, /ready, /status only
make local-demo-curl  # bash examples/local-demo/curl-health-ready.sh
```

These targets **do not** submit evidence, **do not** require API keys, and **do not** mutate the ledger. They are **not** part of **`make oss-diagnostics`** because a running service is not guaranteed in CI sandboxes.

### Public documentation (dashboard)

**Canonical** long-form documentation stays in **`docs/`**. The production-shaped reader UI is the **`dashboard/`** App Router (`app/docs`, `app/help`). **Canonical** prose is not duplicated in a second Mintlify tree in this repository.

## 6. Rust tests

```bash
cargo test --manifest-path rust/Cargo.toml
```

## 7. Python tests

With the `python/.venv` activated:

```bash
cd python
python -m pytest
```

If you run `python3 -m pytest python/tests` from the repo root **without** the venv, collection may fail on missing optional deps — use the venv from step 2.

## 8. Optional: audit binary in background (Makefile)

```bash
make audit_bg      # builds and runs rust/src binary; waits for GET /ready
make audit_stop    # when finished
```

## Canonical references

- Quickstart narrative: [quickstart-5min.md](../quickstart-5min.md)
- Golden path / evidence pack: [golden-path.md](../golden-path.md), [evidence-pack.md](../evidence-pack.md)
- GitHub Action (artefact-bound CI): [github-action.md](../github-action.md)
- Runtime evaluate (semantics, **advisory vs enforcement**): [governance/runtime_integration.md](../governance/runtime_integration.md), OpenAPI [`api/govai-http-v1.openapi.yaml`](../../api/govai-http-v1.openapi.yaml)
