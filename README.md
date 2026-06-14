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
4. **Offline validator toolkit** — `govai standards …` and `python -m aigov_py.standards.cli` validate files locally; the evaluation harness (`python/aigov_py/standards/evaluation.py`) regression-checks all `examples/standards/*.valid.json` files.

**Hosted vs portable:** the **hosted audit service** (or self-hosted equivalent) proves append-only ledger behaviour, tenant isolation, and artefact-bound CI paths. **Portable standards** prove **structural** conformance and digest stability on disk — they do **not** by themselves prove ledger history or billing state.

**Non-goals:** standards validators do **not** certify legal compliance, do **not** replace hosted digest gates, and do **not** mutate ledgers or billing.

### Governance standards registry (interchange)

GovAI publishes an **explicit, versioned registry** of portable governance JSON artefacts (`governance_evidence_pack`, `governance_policy_module`, `governance_decision_trace`, `delegation_graph`, `capability_policy`, `trace_verification_plan`) with matching **JSON Schema** files under `schemas/` and deterministic validators in `python/aigov_py/standards/`. External implementers should start with `docs/standards/interchange-specification.md`, `docs/standards/registry.md`, and `docs/standards/conformance.md`.

**Conformance validation** (one JSON object on stdout with `--json`; fields include `ok`, `artifact_type`, `version`, `checks`, `failures`, `warnings`, `digest`):

```bash
govai standards validate --json examples/standards/evidence-pack.valid.json
make standards-conformance
```

`make governance-standards-check` is a no-op placeholder in Core (platform-specific validation lives in GovAI Platform).

### Standards registry and policy pack catalogs

The repository ships **`registry/*.json`** catalogs and **`docs/registry/`** guides. Curated example packs are listed in **`marketplace/manifest.json`**. See **`docs/registry/overview.md`** and **`docs/standards/registry.md`**.

## Releases

Release **versioning**, **cadence**, **compatibility**, and maintainer **runbooks** live under **`docs/releases/`**. The canonical history is **[CHANGELOG.md](CHANGELOG.md)**. Start with **[docs/releases/versioning-policy.md](docs/releases/versioning-policy.md)** and **[docs/releases/release-checklist.md](docs/releases/release-checklist.md)**.

Before tagging, from the repository root:

```bash
make release-readiness-check
make generate-release-notes VERSION=0.2.1 OUT=release-notes.md   # optional draft
```

CI builds release artefacts (Python wheel/sdist, Rust crate package, Docker image) in **`.github/workflows/release-validation.yml`** without publishing to public registries unless explicitly configured elsewhere.

[![Join Discord](https://img.shields.io/badge/Discord-Join%20Community-5865F2?logo=discord&logoColor=white)](https://discord.gg/sRBSafRtE)

## Golden path (local demo, 2 min)

Minimal deterministic local example using the **existing evidence-pack format**:

- `docs/golden-path.md`
- `docs/evidence-pack.md` (generate a minimal customer-ready evidence pack)

## Makefile targets (GovAI Core)

All targets are defined in the repository **`Makefile`**. Common checks:

| Target | Purpose |
|--------|---------|
| `make gate` | Documentation/report gate (`scripts/gate_reports.py`) |
| `make standards-conformance` | Registered interchange validators on example JSON |
| `make enterprise-readiness-check` | Aggregate Core readiness checks (gate, SDK, Cursor plugin, runtime contracts, benchmark) |
| `make validate-changelog` | Keep a Changelog structure and Rust/Python version alignment |
| `make release-readiness-check` | Pre-tag gate: documentation gate, changelog validation, readiness report, `cargo metadata` |
| `make generate-release-notes` | Draft notes from CHANGELOG (`VERSION=` and optional `OUT=`) |
| `make cursor-plugin-check` | Validate + smoke the bundled Cursor plugin |
| `make cursor-plugin-smoke` | MCP bridge smoke test only |
| `make runtime-observability-check` | `/health`, `/ready`, `/status`, `/metrics` contract |
| `make core-runtime-examples-check` | Adoption examples must not reference platform-only routes |
| `make reference-integrations-check` | Reference integration route drift |
| `make reconstructible-demo-check` | Reconstructible demo contract |
| `make runtime-packaging-check` | Runtime packaging contract |
| `make lineage-governance-check` | Lineage governance graph contract |
| `make public-sdk-packages-check` | Public Python SDK package layout |
| `make oss-ecosystem-check` | Auditability benchmark + gate |

**Local demo:** read-only probes against an **operator-provided** audit URL — see **`examples/local-demo/README.md`**. `make local-demo` exits with instructions when Platform scripts are absent (Core does not start a server).

**Fail-closed BLOCKED demo:** after Compose + `python/.venv` + `GOVAI_*` are aligned, run **`bash examples/blocked_deployment.sh`** (checks **`GET /ready`**, posts minimal evidence, asserts **`govai check`** exit code **3**). See **`examples/local-demo/CONTRACT.md`**.

**CI workflows:** `.github/workflows/govai-ci.yml` (portable Core CI), `.github/workflows/oss-developer-experience.yml` (`make cursor-plugin-check`, `make enterprise-readiness-check`), `.github/workflows/supply-chain-audit.yml` (`cargo audit`, `pip-audit`), `.github/workflows/security-scan.yml` (gitleaks, Trivy).

Contributor-oriented Makefile targets also include evidence-pack flows (`make bundle`, `make verify_cli`), demo drivers (`make demo`, `make flow`), and engineering helpers (`make env_check`, `make engineering_loc`). These require **`GOVAI_AUDIT_BASE_URL`** / **`RUN_ID`** where noted in the Makefile — Core does not background-manage a localhost audit server.

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

Equivalent wrapper (same script; JSON summary on stdout, progress on stderr):

```bash
export GOVAI_AUDIT_BASE_URL=http://127.0.0.1:8088
export GOVAI_API_KEY=test-key
bash examples/blocked_deployment.sh
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

- `make enterprise-readiness-check` — aggregate Core readiness checks (see Makefile targets section above)
- `make gate` — documentation/report gate

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

