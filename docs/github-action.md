# GitHub Actions: GovAI artefact-bound compliance gate

**See also:** [cli-reference.md](cli-reference.md) (`verify-evidence-pack`, `submit-evidence-pack`, exit codes), [api-reference.md](api-reference.md) (`/bundle-hash`, `/api/export/:run_id`, `/compliance-summary`), [customer-quickstart.md](customer-quickstart.md) (minimal curl + `govai check`).

```docs
preset: github-workflow
```

```docs
preset: ci-artifacts
```

This repository publishes a reusable **composite GitHub Action** that installs the GovAI CLI from **PyPI** (`aigov-py==0.2.1`, same version as `python/pyproject.toml`) and runs the **production semantic path**:

1. `govai submit-evidence-pack` — replays CI-generated evidence events from `<artifacts_path>/<run_id>.json` to the hosted ledger.
2. `govai verify-evidence-pack` — **mandatory:** hosted **`GET /bundle-hash`** digest **`events_content_sha256`** matches **`evidence_digest_manifest.json`**. By default the action also passes **`--require-export`**: cross-check **`GET /api/export/:run_id`** against that digest (set input **`require_export: false`** only if you accept a weaker audit cross-check). **Then** a **`VALID`** compliance verdict from **`GET /compliance-summary`**.

**PyPI pin:** the install pin **must** match `version` in `python/pyproject.toml` for the tag you use; drift breaks CI vs local reproducibility.

## Version bump checklist (keep in lockstep)

When you bump the released version (tag / PyPI publish), update these together so the action runtime, workflow usage, Python pin, and docs remain consistent:

- `action.yml` (root composite action)
- `.github/actions/govai-check/action.yml` (local action implementation)
- `.github/workflows/compliance.yml` (hosted gate workflow pin/usage)
- `python/pyproject.toml` (PyPI package version)
- `docs/github-action.md` (this doc, including the pin shown in examples)

**Export cross-check (`require_export`):** the composite action defaults **`require_export`** to **`true`**, so **`verify-evidence-pack`** runs with **`--require-export`**. That is part of the **full audit guarantee** in CI: hosted **`GET /api/export/:run_id`** must be available and consistent with the digest chain, not only **`GET /compliance-summary`**. Set **`require_export: false`** only when you explicitly accept a weaker gate.

**Ledger tenant vs `X-GovAI-Project`:** ledger isolation is derived **only** from the API key (`GOVAI_API_KEYS_JSON`). The `project` input sets **`X-GovAI-Project`** for optional metadata / usage labels; it **does not** isolate ledger data.

A green job using **this action** therefore means CI artefacts were anchored by digest on the ledger and evaluated as **`VALID`** — **not** merely that the hosted API accepted an ad-hoc or synthetic submission.

**`govai check` alone** does **not** prove artefact continuity; treat it as a policy readout **without** cryptographic binding to CI outputs. Prefer **`submit-evidence-pack` + `verify-evidence-pack`** for anything that behaves as a release gate.

**CI integration:** this composite action is the artefact-bound CI integration. The currently supported customer-facing decision endpoint is `GET /compliance-summary`. Runtime decision APIs are separate hardening work and are not documented as available in this branch.

## Golden path (local, deterministic)

If you want a minimal **copy/paste** example that uses the same **evidence pack** format as CI (`<run_id>.json` + `evidence_digest_manifest.json`) and shows `BLOCKED → VALID`, see:

- `docs/golden-path.md`

## Synthetic smoke workflow (explicitly labelled)

Manual workflow **`.github/workflows/govai-smoke.yml`** is labelled **SYNTHETIC SMOKE TEST ONLY**. It pushes scripted curls and optionally runs **`govai check`**; it runs **only** on **`workflow_dispatch`** — not automatically on merges to **`main`**. Use it for demos and connectivity probes, never as proof of artefact-bound production compliance.

Authoritative artefact-bound production gate for this repo: **`.github/workflows/compliance.yml`**, **`govai-compliance-gate`** (after **`evidence_pack`**).

## Configure branch protection so this job is required before merges

**Required (production):** require the **`.github/workflows/compliance.yml`** workflow and, specifically, a job that runs the same artefact-bound path as **`govai-compliance-gate`** (hosted **`submit-evidence-pack` + `verify-evidence-pack`** with real CI artefacts). You may also require the composite action from this repo with downloaded artefacts if that is your only hosted gate.

**Do not** treat the following as sufficient for production on their own:

- **`.github/workflows/govai-smoke.yml`** — manual **synthetic** smoke only (`workflow_dispatch`), not an artefact-bound merge gate.
- **`govai check`** (or a job that only runs **`check`**) — policy readout **without** cryptographic binding to CI **`evidence_digest_manifest.json`**.

Point required checks at the workflow/job that invokes **`submit-evidence-pack` + `verify-evidence-pack`** **with real CI artefacts**.

## Action behaviour

- Sets up **Python 3.11**
- Installs **`aigov-py==0.2.1`** from PyPI
- Validates **`artifacts_path`** is an existing directory
- Runs **`submit-evidence-pack`** then **`verify-evidence-pack`** with **`--path`** and **`--run-id`** (passes **`--require-export`** by default; set **`require_export: false`** to omit)
- Exit codes propagated from **`verify-evidence-pack`**: **`1`** ERROR (infra/digest/export), **`2`** INVALID, **`3`** BLOCKED, **`4`** USAGE (`python/aigov_py/cli_exit.py`)

## Official action reference

Publish path (example):

`your-org/your-repo@<tag>` (root **`action.yml`**), or `./.github/actions/govai-check` for forks.

## Inputs

| Input | Required | Purpose |
|--------|----------|---------|
| **`run_id`** | Yes | Must match the ledger id and CI artefact names: **`docs/reports/<run_id>.md`**, **`<run_id>.json`**, and the digest manifest. Composite-action callers supply any id they control (UUID, product id, etc.). **This repo’s `compliance.yml`** emits **`basename-${{ github.run_id }}-${{ github.run_attempt }}`** for hosted runs (one **`docs/reports/<basename>.md`** per PR; CI copies it to **`docs/reports/<run_id>.md`** before **`make run`**) so workflow reruns do not reuse a stale hosted ledger row for the same basename. |
| **`artifacts_path`** | Yes | Directory containing **`evidence_digest_manifest.json`** and `<run_id>.json` (e.g. from **`actions/download-artifact`**). **`events_content_sha256`** in the manifest is the **source-of-truth** digest checked against **`GET /bundle-hash`**. |
| **`base_url`** | Yes | GovAI audit base URL (**`GOVAI_AUDIT_BASE_URL`**). |
| **`api_key`** | Yes | Bearer token (**`GOVAI_API_KEY`** secret). |
| **`project`** | No (default **`github-actions`**) | Sent as **`X-GovAI-Project`** (metadata / usage label). **Not** ledger tenant isolation (that comes from the API key only). |
| **`require_export`** | No (default **`true`**) | When **`true`** (default), passes **`--require-export`** so a missing or failed **`/api/export`** cross-check fails the step (exit **1**). Set **`false`** only if you explicitly accept a weaker gate. |

## Required repository secrets / variables

- **`GOVAI_AUDIT_BASE_URL`** (repository variable recommended)
- **`GOVAI_API_KEY`** (secret)

## Minimal usage (caller supplies downloaded artefact dir)

```yaml
jobs:
  govai-hosted-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/download-artifact@v4
        with:
          name: evidence_packs
          path: artefacts

      - name: Artefact-bound GovAI gate
        uses: MonikaDvorackova/aigov-compliance-engine@v1
        with:
          run_id: ${{ vars.GOVAI_RUN_ID }}
          artifacts_path: artefacts
          base_url: ${{ vars.GOVAI_AUDIT_BASE_URL }}
          api_key: ${{ secrets.GOVAI_API_KEY }}
```

## Minimal “example customer repo” layout (what your repo should contain)

This is the smallest practical shape that is easy to copy and hard to misuse. Your repo produces:

- **`evidence_digest_manifest.json`** (digest manifest)
- **`<run_id>.json`** (evidence bundle)

and then runs the composite action against the directory that contains both.

Suggested layout:

```text
.
├── .github/workflows/compliance.yml
└── artefacts/
    ├── evidence_digest_manifest.json
    └── <run_id>.json
```

Minimal workflow snippet (caller supplies artefacts, then gates):

```yaml
name: compliance
on:
  pull_request:
    branches: [ main ]

jobs:
  govai:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Your pipeline step(s) must create / download:
      # - artefacts/evidence_digest_manifest.json
      # - artefacts/<run_id>.json

      - name: GovAI artefact-bound compliance gate
        uses: MonikaDvorackova/aigov-compliance-engine@v1
        with:
          run_id: ${{ vars.GOVAI_RUN_ID }}
          artifacts_path: artefacts
          base_url: ${{ vars.GOVAI_AUDIT_BASE_URL }}
          api_key: ${{ secrets.GOVAI_API_KEY }}
```

## Example misconfiguration (**USAGE / exit 4**)

Missing **`artifacts_path`**, **`api_key`**, or missing directory → action exits **`4`** with **`::error::`** annotations.

## Verdict semantics

| CLI exit | Meaning |
|----------|---------|
| **0** | **`VERIFY_OK`**: digest continuity verified and verdict **`VALID`**. |
| **1** | Error: transport, manifest/bundle-hash mismatch, export inconsistency — not a verdict. |
| **2** | Verdict **`INVALID`**. |
| **3** | Verdict **`BLOCKED`**. |
| **4** | Usage/configuration (missing **`run_id`** / artefacts). |

**Server-aligned verdict meanings** (same order as `GET /compliance-summary`):

- **`INVALID`** — evaluation explicitly failed (`evaluation_passed == false`).
- **`BLOCKED`** — missing required evidence, missing risk/human approval, not yet promoted, digest/trace prerequisites not met, or any other “not yet eligible” state.
- **`VALID`** — evaluation passed, approvals satisfied, promotion recorded.

**Operational probes:** see **`docs/hosted-backend-deployment.md` → “HTTP startup and operational probes”** for the canonical contract of **`GET /health`** (liveness-only, after successful startup) vs **`GET /ready`** (authoritative readiness: DB + migrations + ledger writability).

## Runtime decision API (non-CI)

For non-CI enforcement, call `GET /compliance-summary` with the same `run_id` after evidence submission. Runtime decision APIs are planned separately and are not part of this branch.

## Billing (minimal)

Hosted service exposes **`POST /stripe/webhook`** (Stripe-signed, idempotent event log) and **`GET /billing/usage-summary`** (Bearer auth). See **[billing.md](billing.md)** for limitations and env vars.

## Local dev (this repo)

```yaml
- uses: ./.github/actions/govai-check
  with:
    run_id: ${{ needs.build.outputs.report_run_id }}
    artifacts_path: downloaded-artefacts-dir
    base_url: ${{ vars.GOVAI_AUDIT_BASE_URL }}
    api_key: ${{ secrets.GOVAI_API_KEY }}
```

## CLI install (without composite action)

```bash
python -m pip install --upgrade pip
python -m pip install "aigov-py==0.2.1"
govai verify-evidence-pack --path ./artefacts --run-id "$GOVAI_RUN_ID"
```

See also: **[customer-quickstart.md](customer-quickstart.md)** (update install pin after release tagging).
