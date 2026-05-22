# Technical documentation

**Authoritative layout for the current implementation:** [ARCHITECTURE.md](../ARCHITECTURE.md), [DEMO_FLOW.md](../DEMO_FLOW.md), [OPEN_SOURCE_SCOPE.md](../OPEN_SOURCE_SCOPE.md). **Canonical HTTP v1 contract:** [`api/govai-http-v1.openapi.yaml`](../api/govai-http-v1.openapi.yaml). This file retains a compact technical summary.

## Scope

Implemented scope:

- Tamper-evident audit logging (hash-chained JSONL records)
- Policy-as-code enforcement before append (`v0.4_human_approval`)
- Dataset fingerprint and governance fields in `data_registered`
- Per-run exportable evidence bundle and Markdown report

---

## Product Scope

GovAI is a CI compliance gate for AI systems with audit evidence export.

**Production semantics** (recommended for release / promoted branches): artefact-bound flow — **`govai submit-evidence-pack`** replays CI-generated **`events`**, **`govai verify-evidence-pack`** **requires** hosted **`events_content_sha256`** from **`GET /bundle-hash`** to match **`evidence_digest_manifest.json`**, **then** **`GET /compliance-summary`** **`VALID`**. A cross-check against **`GET /api/export/:run_id`** is **optional** by default (if the export is unavailable, the CLI logs that the cross-check was skipped). Pass **`--require-export`** to treat a missing or inconsistent export as exit code **1** (ERROR), not a silent pass.

Synthetic smoke or **`govai check`** without digest verification proves policy reachability for *some* evidence stream, **not** that *your CI bundle* was cryptographically anchored on the ledger. The authoritative production gate in this repository is **`.github/workflows/compliance.yml`** (job **`govai-compliance-gate`**) and the root **`action.yml`** / **`.github/actions/govai-check`** composite action when wired to real CI **`artifacts_path`**. Do **not** treat **`.github/workflows/govai-smoke.yml`** (manual smoke only) or **`govai check` alone** as a production release gate. Every protected-branch merge that ships report evidence should require a workflow that runs hosted **`submit-evidence-pack`** + **`verify-evidence-pack`** (same semantics as the production gate).

Core HTTP surface:

- accepts evidence via POST /evidence
- enforces policy constraints at write time
- produces deterministic decision via GET /compliance-summary
- **production gate**: artefact-bound submit + verify (digest + VALID), not **`check`** alone
- exports audit data via GET /api/export/:run_id

Guarantees:

- deterministic decision for given evidence + policy_version
- append-only evidence log
- hash chaining integrity

Non-guarantees:

- not a legal certification
- not full compliance coverage
- does not generate missing evidence

## When to use GovAI

- deploying ML models via CI/CD
- enforcing approval workflows before release
- requiring audit evidence for decisions

## Decision states

VALID:  
All required evidence present. Deployment allowed.

INVALID:  
Evidence present but fails policy. Deployment rejected.

BLOCKED:  
Not eligible for promotion (missing evidence and/or unmet approval/promotion prerequisites). Deployment halted.

## Pricing

Free:

- limited runs per month
- limited events per run
- includes:
  - compliance summary
  - CI gate
  - audit export

Pro:

- higher limits
- includes everything in Free

Enterprise:

- custom limits
- includes:
  - SLA
  - security review support
  - custom policy configuration

Note:
Limits are exposed via GET /usage.

## Auditability and Trust

- append-only logs
- hash chaining (prev_hash → record_hash)
- deterministic decision (policy_version)
- exportable audit JSON

## Rust evidence service (`rust/`)

- **Ingest:** `POST /evidence` — body: `EvidenceEvent` (`event_id`, `event_type`, `ts_utc`, `actor`, `system`, `run_id`, `payload`).
- **Usage / export:** `GET /usage`, `GET /api/export/:run_id`.
- **Chain:** `GET /verify`, `GET /verify-log`
- **Bundle:** `GET /bundle?run_id=…`, `GET /bundle-hash?run_id=…` (also returns **`events_content_sha256`** — portable SHA-256 over canonicalised evidence events minus server `environment`; see **`bundle::portable_evidence_digest_v1`** — used for artefact-bound production gates alongside legacy **`bundle_sha256`** tied to **`log_path` / tier** metadata)
- **Summary:** `GET /compliance-summary?run_id=…` — `ok`, `schema_version` (`aigov.compliance_summary.v2`), `policy_version`, `run_id`; when `ok` is true — `verdict` (`VALID` / `INVALID` / `BLOCKED`) and `current_state` (inner `schema_version`: `aigov.compliance_current_state.v2`, same projection as bundle `identifiers` for canonical fields).
- **Storage:** append-only JSONL ledger files.
  - Dev default: relative to process cwd (local-friendly).
  - Staging/prod: requires `GOVAI_LEDGER_DIR` pointing to a **persistent** directory (service fails fast otherwise).
- **Other:** `GET /status` (`ok`, `policy_version`, `environment`); `GET /ready` and `GET /health` are defined canonically in **`docs/hosted-backend-deployment.md` → “HTTP startup and operational probes”**.

Authenticated routes (Supabase JWT; **stable** enterprise surface): `GET /api/me`, `POST /api/assessments`, `/api/compliance-workflow*` — see OpenAPI.

## Python ML pipeline

- `python -m aigov_py.pipeline_train` — sklearn `LogisticRegression` on Iris; posts events to `AIGOV_AUDIT_URL` (default `http://127.0.0.1:8088`).

## Policy / event sequence (enforced in Rust)

The policy enforces payload shapes and ordering for a governed promotion path, including:

- `data_registered` (dataset + governance metadata + `dataset_governance_commitment`, `ai_system_id`, `dataset_id`, …)
- `model_trained` (after `data_registered` for the same `run_id`)
- `evaluation_reported` (metric / threshold / passed)
- `risk_recorded` → `risk_mitigated` → `risk_reviewed` (assessment and risk linkage)
- `human_approved` (linkage to assessment, risk, dataset commitment, scope)
- `model_promoted` (evaluation passed, approved human and risk review linkage)

See `rust/src/policy.rs` for the exact rules.

## Exports and Makefile

- `make bundle RUN_ID=…` → `aigov_py.export_bundle` (expects `docs/evidence/<RUN_ID>.json` and `docs/reports/<RUN_ID>.md`).
- `make report_prepare RUN_ID=…` → fetch evidence, render report, export bundle, verify CLI.

## Integrity

- `make verify` — calls `GET /verify` on the running service (full chain).

## EU AI Act (mapping only)

Mechanisms above can be described in terms of Articles 9–13 (risk, data, documentation, logging, transparency) as a framing for engineering mechanisms. Mapping does not imply regulatory completeness.
