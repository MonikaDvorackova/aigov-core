# Contributor workflow (GovAI)

Evidence-first, **fail-closed** semantics apply across the product; contributor mechanics mirror that discipline in **CI documentation gates** and **branch policy**.

## Branches

1. **`staging`** — default integration branch for features and docs from contributors.
2. **`main`** — promotion target; **only** via **`staging` → `main`** for this repository’s release discipline.

Create your work branch **from up-to-date `staging`**:

```bash
git fetch origin
git switch staging
git pull --ff-only origin staging
git switch -c your-handle/short-topic
```

Open pull requests **to `staging`** for normal work. Do **not** open contributor PRs **from `main`**.

## Pull request to `staging`

- Use the **[`.github/pull_request_template.md`](../../.github/pull_request_template.md)** checklist.
- Link an issue when possible.
- Call out if you touch **enforcement**, **evidence**, **tenant isolation**, or **verdict** semantics — those need explicit review.

## Promotion `staging` → `main`

Maintainers promote through a dedicated PR **`staging` → `main`**. Follow **[docs/contributor-branch-workflow.md](../contributor-branch-workflow.md)** and branch policy workflows if you are preparing that promotion.

## Audit reports (`docs/reports/`)

- **Core-affecting** changes (Rust, Python, `Makefile`, `scripts/`, selected contracts) trigger the **artefact-bound** compliance workflow, which expects **exactly one** distinct **`docs/reports/<basename>.md`** change per PR (except the special **`staging` → `main`** promotion aggregate). Split work if you need multiple report basenames.
- **Every** file matching **`docs/reports/*.md`** must include the exact headings **`## Evaluation gate`** and **`## Human approval gate`** (see **`scripts/gate_reports.py`**).

## Validation commands (local)

From repo root:

```bash
python3 scripts/gate_reports.py   # or: make gate
make oss-health                     # key OSS files on disk (stdlib; no network)
make oss-metrics                    # repository size metrics (stdout only)
make docs-links                     # local Markdown links (non-strict; see --strict in Makefile)
make oss-diagnostics                # oss-health + oss-metrics + docs-links-strict + oss-diagnostics + gate
make enterprise-readiness-check     # security-trust + trust-manifest + commercial-readiness + oss-diagnostics (OSS CI)
make pilot-execution                # pilot/sales package diagnostics (stdlib)
make pilot-manifest                 # validate docs/pilots/pilot-manifest.json
make pilot-check                    # pilot-execution + pilot-manifest + gate
make customer-operations            # customer operations diagnostics (stdlib)
make customer-operations-manifest   # validate docs/operations/customer-operations-manifest.json
make production-readiness-checklist # checklist generator smoke
make customer-operations-check      # customer-operations + customer-operations-manifest + production-readiness-checklist + gate
make partner-ecosystem              # partner ecosystem diagnostics (stdlib)
make partner-ecosystem-manifest     # validate docs/partners/partner-ecosystem-manifest.json
make partner-certification-package  # certification package generator smoke
make partner-ecosystem-check        # partner-ecosystem + partner-ecosystem-manifest + partner-certification-package + gate
make regulatory-evidence            # regulatory diagnostics (stdlib)
make regulatory-manifest            # validate docs/regulatory/regulatory-evidence-manifest.json
make ai-act-obligations             # validate docs/regulatory/ai-act-obligations.json
make regulatory-export              # Markdown export generator smoke
make regulatory-check               # regulatory-evidence + regulatory-manifest + ai-act-obligations + regulatory-export + gate
make observability                  # observability diagnostics (stdlib)
make observability-manifest         # validate docs/observability/observability-manifest.json
make operational-snapshot           # validate examples/observability/sample-operational-snapshot.json
make operational-health-score       # deterministic JSON scoring with risk_level and findings
make operational-intelligence-report # Markdown intelligence report generator smoke
make observability-check            # observability + observability-manifest + operational-snapshot + operational-health-score + operational-intelligence-report + gate

make runtime-safety                 # runtime safety diagnostics (stdlib)
make runtime-safety-manifest        # validate docs/runtime-safety/runtime-safety-manifest.json
make runtime-safety-snapshot        # validate examples/runtime-safety/sample-runtime-safety-snapshot.json
make runtime-safety-score           # deterministic runtime safety JSON scoring
make runtime-safety-report          # Markdown runtime safety report generator smoke
make runtime-safety-check           # runtime-safety + runtime-safety-manifest + runtime-safety-snapshot + runtime-safety-score + runtime-safety-report + gate
make hosted-platform                # hosted platform readiness diagnostics (stdlib)
make hosted-platform-manifest       # validate docs/hosted-platform/hosted-platform-manifest.json
make hosted-readiness-snapshot      # validate examples/hosted-platform/sample-hosted-readiness-snapshot.json
make hosted-readiness-score         # deterministic hosted readiness JSON (sample)
make hosted-readiness-export        # customer-facing Markdown export smoke
make hosted-platform-check          # hosted-platform + validators + score + export + gate

make evidence-quality               # evidence quality diagnostics (stdlib)
make evidence-quality-manifest      # validate docs/evidence-quality/evidence-quality-manifest.json
make dataset-provenance-snapshot    # validate examples/evidence-quality/sample-dataset-provenance-snapshot.json
make evidence-quality-score         # deterministic evidence quality JSON scoring
make dataset-governance-report      # Markdown dataset governance report generator smoke
make evidence-quality-check         # evidence-quality + manifest + snapshot + score + report + gate

make hosted-platform                # hosted platform readiness diagnostics (stdlib)
make hosted-platform-manifest       # validate docs/hosted-platform/hosted-platform-manifest.json
make hosted-readiness-snapshot      # validate examples/hosted-platform/sample-hosted-readiness-snapshot.json
make hosted-readiness-score         # deterministic hosted readiness JSON scoring
make hosted-readiness-export        # customer-facing Markdown export smoke
make hosted-platform-check          # hosted-platform + manifest + snapshot + score + export + gate
make model-risk                     # model risk diagnostics (stdlib)
make model-risk-manifest            # validate docs/model-risk/model-risk-manifest.json
make model-evaluation-snapshot      # validate examples/model-risk/sample-model-evaluation-snapshot.json
make model-risk-score               # deterministic model risk JSON (sample)
make model-assurance-report         # assurance Markdown generator smoke
make model-risk-assurance-check     # model-risk + manifest + snapshot + score + report + gate

make agent-governance               # agent governance diagnostics (stdlib)
make agent-governance-manifest      # validate docs/agent-governance/agent-governance-manifest.json
make agent-delegation-snapshot      # validate examples/agent-governance/sample-agent-delegation-snapshot.json
make agent-governance-score         # deterministic governance score smoke (sample JSON)
make agent-governance-report        # Markdown governance report generator smoke
make agent-governance-check         # agent-governance + manifest + snapshot + score + report + gate

make public-launch                  # public launch and ecosystem standardization diagnostics (stdlib)
make public-launch-manifest         # validate docs/launch/public-launch-manifest.json
make standardization-readiness-snapshot  # validate sample standardization readiness snapshot
make public-launch-readiness-score  # deterministic readiness JSON scoring
make public-launch-report           # deterministic Markdown report generation
make public-launch-check            # public-launch + manifest + snapshot + score + report + gate
make marketplace                    # marketplace diagnostics (stdlib)
make marketplace-manifest           # validate docs/marketplace/marketplace-manifest.json
make extension-package              # validate examples/marketplace/sample-extension-package.json
make marketplace-listing            # listing generator smoke
make marketplace-check              # marketplace + marketplace-manifest + extension-package + marketplace-listing + gate
make customer-analytics             # customer analytics diagnostics (stdlib)
make customer-analytics-manifest    # validate docs/analytics/customer-analytics-manifest.json
make customer-health-score          # health score smoke (sample JSON)
make executive-business-review      # EBR generator smoke (sample JSON)
make customer-analytics-check        # customer-analytics + customer-analytics-manifest + customer-health-score + executive-business-review + gate
make policy-intelligence             # policy intelligence diagnostics (stdlib)
make policy-intelligence-manifest    # validate docs/policy-intelligence/policy-intelligence-manifest.json
make governance-control-snapshot     # validate examples/policy-intelligence/sample-governance-control-snapshot.json
make policy-coverage-score           # smoke: deterministic JSON scoring for sample governance snapshot
make governance-control-report       # smoke: governance Markdown report from sample snapshot
make policy-intelligence-check       # policy-intelligence + policy-intelligence-manifest + governance-control-snapshot + policy-coverage-score + governance-control-report + gate
make control-plane                   # Phase 23 control-plane diagnostics (stdlib)
make control-plane-manifest          # validate docs/control-plane/control-plane-manifest.json
make governance-posture-snapshot     # validate examples/control-plane/sample-governance-posture-snapshot.json
make governance-posture-score        # deterministic JSON scoring for sample posture snapshot
make control-plane-report            # deterministic Markdown report from sample posture snapshot
make governance-posture-check                   # control-plane + manifest + snapshot + score + report + gate
make developer-integrations          # developer integrations diagnostics (stdlib)
make developer-integrations-manifest # validate docs/integrations/developer-integrations-manifest.json
make automation-pack                 # validate examples/integrations/sample-automation-pack.json
make automation-pack-summary         # automation pack summary generator smoke
make developer-integrations-platform-check # developer-integrations + developer-integrations-manifest + automation-pack + automation-pack-summary + gate
make release-manifest               # validate docs/releases/release-manifest.json (stdlib JSON)
make validate-changelog             # Keep a Changelog gate for CHANGELOG.md
make generate-release-notes         # deterministic sample notes under examples/releases/
make release-readiness-report       # aggregated JSON readiness (manifest + changelog + operations + Makefile)
make release-readiness-check        # release-operations-check + release-manifest + validate-changelog + release-readiness-report + docs-links-strict + gate
cargo test --manifest-path rust/Cargo.toml
```

Python (activate **`python/.venv`** first):

```bash
cd python
pytest
python -m pytest \
  tests/test_validate_release_manifest.py \
  tests/test_validate_changelog.py \
  tests/test_generate_release_notes.py \
  tests/test_release_readiness_report.py \
  tests/test_validate_regulatory_evidence_manifest.py \
  tests/test_validate_ai_act_obligations.py \
  tests/test_regulatory_evidence_check.py \
  tests/test_generate_regulatory_evidence_export.py \
  tests/test_validate_observability_manifest.py \
  tests/test_validate_operational_snapshot.py \
  tests/test_operational_health_score.py \
  tests/test_observability_check.py \
  tests/test_generate_operational_intelligence_report.py \
  tests/test_validate_runtime_safety_manifest.py \
  tests/test_validate_runtime_safety_snapshot.py \
  tests/test_runtime_safety_score.py \
  tests/test_runtime_safety_check.py \
  tests/test_generate_runtime_safety_report.py \
  tests/test_validate_hosted_platform_manifest.py \
  tests/test_validate_hosted_readiness_snapshot.py \
  tests/test_hosted_readiness_score.py \
  tests/test_hosted_platform_check.py \
  tests/test_generate_hosted_readiness_export.py \
  tests/test_validate_agent_governance_manifest.py \
  tests/test_validate_agent_delegation_snapshot.py \
  tests/test_agent_governance_score.py \
  tests/test_agent_governance_check.py \
  tests/test_generate_agent_governance_report.py \
  tests/test_validate_public_launch_manifest.py \
  tests/test_validate_standardization_readiness_snapshot.py \
  tests/test_public_launch_readiness_score.py \
  tests/test_public_launch_check.py \
  tests/test_generate_public_launch_report.py \
  -q
python -m pytest tests/test_validate_developer_integrations_manifest.py tests/test_validate_automation_pack.py tests/test_developer_integrations_check.py tests/test_generate_automation_pack_summary.py -q
python -m pytest tests/test_validate_evidence_quality_manifest.py tests/test_validate_dataset_provenance_snapshot.py tests/test_evidence_quality_score.py tests/test_evidence_quality_check.py tests/test_generate_dataset_governance_report.py -q
```

If **`pytest`** fails on missing **`nacl`**, install the editable package:

```bash
pip install -e ".[dev]"
```

inside **`python/`**.

## Advisory vs enforcement (terminology)

- **`GET /compliance-summary`** remains the **authoritative** promotion verdict for the evidence pipeline described in customer docs.
- **`POST /v1/runtime/evaluate`** may surface **`governance_summary`** overlays; **advisory** evaluations (for example **`advisory_control_evaluations`**, **`source: capability_shadow`**) are **observability-only** and **must not** be interpreted as replacing core **fail-closed** ingest or compliance-summary **VALID / INVALID / BLOCKED** semantics.

## Where to read more

- **[CONTRIBUTING.md](../../CONTRIBUTING.md)** — testing expectations and principles.
- **[docs/github-action.md](../github-action.md)** — artefact-bound CI semantics.
- **[docs/governance/runtime_integration.md](../governance/runtime_integration.md)** — runtime evaluate enrichment model.
