# Customer onboarding (self-serve hosted, ~10 minutes)

Goal: go from **zero → `BLOCKED` → `VALID`** using the dashboard wizard or supported CLI commands — no source code reading.

## Self-service path (dashboard)

1. Sign up at `/signup` on your GovAI dashboard deployment.
2. Complete **Getting started** (`/getting-started`): organization name, Stripe checkout (Hosted Professional — configure `GOVAI_STRIPE_PRICE_PRO` on the audit service), one-time API key reveal, CI/CLI steps, verdict review, export.
3. Use the issued API key as `GOVAI_API_KEY` below.

API routes (JWT): `POST /api/onboarding/provision`, `POST /api/onboarding/api-keys`, `POST /api/onboarding/billing/checkout-session`. See [reports/self-service-onboarding-foundation.md](reports/self-service-onboarding-foundation.md).

## CLI path (after dashboard provisioning)

You need:

- `GOVAI_AUDIT_BASE_URL` (your hosted audit API base URL)
- `GOVAI_API_KEY` (from the dashboard one-time reveal, or operator-provisioned for legacy pilots)

This doc uses the **evidence pack** flow (same shape as CI):

`govai evidence-pack init` → `govai submit-evidence-pack` → `govai verify-evidence-pack --require-export` → `govai check`

If you want background and exact file shape, see [evidence-pack.md](evidence-pack.md).

## Prereqs

- Python 3.10+
- A working hosted GovAI audit backend (operator responsibility):
  - `GET /ready` returns HTTP 200 (not just `/health`)

## 1) Install the CLI

```bash
python -m pip install --upgrade pip
python -m pip install "aigov-py==0.2.1"
govai --version
```

## 2) Configure audit service URL and API key

```bash
export GOVAI_AUDIT_BASE_URL="https://audit.example.com"
export GOVAI_API_KEY="YOUR_API_KEY"
```

Preflight (fail-safe: validates local evidence pack + requires backend readiness):

```bash
govai preflight
```

Sanity check (must be 200):

```bash
govai ready
```

## 3) Copy-paste runnable onboarding flow (one run id, one out dir)

This block is the supported customer flow. It uses an explicit `RUN_ID` and `OUT_DIR` and reuses the **same** `RUN_ID` through init → submit → verify → check.

```bash
set -euo pipefail

export RUN_ID="$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"
export OUT_DIR="./evidence_pack_${RUN_ID}"

echo "RUN_ID=$RUN_ID"
echo "OUT_DIR=$OUT_DIR"

# a) generate evidence pack (writes: <run_id>.json + evidence_digest_manifest.json)
govai evidence-pack init --out "$OUT_DIR" --run-id "$RUN_ID"

# b) submit evidence pack to the hosted ledger (append-only)
govai submit-evidence-pack --path "$OUT_DIR" --run-id "$RUN_ID"

# c) verify digest continuity + require export cross-check + require VALID
govai verify-evidence-pack --require-export --path "$OUT_DIR" --run-id "$RUN_ID"

# d) read the authoritative verdict (still must be VALID to exit 0)
govai check --run-id "$RUN_ID"
```

## 4) Interpret results (VALID / BLOCKED / INVALID)

`govai check` prints the verdict on stdout and exits non-zero unless the verdict is **`VALID`**.

- **`VALID`**: all required evidence is present, evaluation passed, and promotion prerequisites are satisfied. Deployment allowed.
- **`BLOCKED`**: evidence is incomplete or prerequisites (risk/human approval/promotion/digest/export) are not satisfied yet. This is not “failed”; it means “not eligible yet”. Fix is to provide the missing evidence for the same `RUN_ID`.
- **`INVALID`**: evaluation explicitly failed policy rules. This is a real failure; fix the underlying issue, then produce new evidence and re-check.

Important: **Do not assume you can reach `VALID` without `submit` + `verify` + `check`.** `verify-evidence-pack` is the artefact/digest continuity gate; `check` is the verdict readout.

## Troubleshooting (first-run failures)

If you get stuck, capture the exact command output and start with:

```bash
govai health
govai status
govai ready
govai check --run-id "$RUN_ID"
```

Most common issues:

- **`/ready` not 200**: the backend is not operationally ready (DB/migrations/ledger). This is an operator issue, not a policy verdict. Fix the environment until `govai ready` succeeds.
- **Missing or wrong `GOVAI_AUDIT_BASE_URL`**: you are pointing at the wrong environment or an invalid base URL. Re-export `GOVAI_AUDIT_BASE_URL` and re-run `govai ready`.
- **Missing or wrong `GOVAI_API_KEY`**: auth failure (often 401). Re-export `GOVAI_API_KEY` for the correct environment/tenant.
- **`APPEND_ERROR`** during `submit-evidence-pack`: the server rejected an evidence append (commonly wrong ordering/prereqs, wrong tenant key, or a backend ledger/DB issue). Re-check `govai ready`, confirm the correct API key, and retry submit.
- **`RUN_NOT_FOUND`**: the run does not exist in the tenant/ledger you’re querying (wrong `RUN_ID`, wrong base URL, or wrong API key/tenant). Ensure you use the same `RUN_ID` you submitted and the correct `GOVAI_API_KEY` for that environment.
- **Digest mismatch** (**digest mismatch**, verify fails): the local `evidence_digest_manifest.json` does not match the hosted `/bundle-hash` for that `RUN_ID`. Regenerate the evidence pack and re-run `submit` then `verify` for the same `RUN_ID`, or use a fresh `RUN_ID` to eliminate stale/partial ingestion.
- **`BLOCKED` because evidence is incomplete**: `govai check` will print `BLOCKED` and explain missing evidence / blocked reasons. The fix is to submit the missing evidence (in real customer integration this comes from your CI/app pipeline, not this demo pack).

For a broader matrix, see [troubleshooting.md](troubleshooting.md).

## What to do next

- **Integrate the CI gate** (artefact-bound): see [github-action.md](github-action.md).
- **Understand the evidence pack shape**: see [evidence-pack.md](evidence-pack.md).
- **Manual evidence control** (advanced): see [manual-evidence-flow.md](manual-evidence-flow.md).
