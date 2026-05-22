# Operator runbook

Goal: keep the system healthy, unblock customers quickly, and separate infra failures from evidence/policy outcomes.

## Minimum healthy system

A minimum healthy system satisfies all of the following:

- The API process is reachable and responsive.
- The backing database is reachable and migrations/schema are current.
- The ledger/event store is writable/readable (evidence ingestion works).
- API keys are configured and valid (operators + customer tokens).
- A run can be created/located and evaluated deterministically given complete evidence.

## /health vs /status vs /ready

Use these in order:

- `/health` (liveness)
  - Answers: “Is the service up and responding?”
  - Should be fast and not require deep dependencies.
  - Operator use: quick check after deploy/restart; network/DNS sanity.

- `/status` (shallow diagnostics)
  - Answers: “Is the service generally operational?”
  - May check basic dependencies but can still be green while deeper requirements are missing.
  - Operator use: confirm API config present; see coarse dependency status.

- `/ready` (readiness to evaluate)
  - Answers: “Can the system actually execute evaluations end-to-end now?”
  - Typically requires: DB ok, ledger ok, any required keys/config present, and internal components initialized.
  - Operator use: gate before declaring an environment usable for customers/CI.

### Readiness contract (authoritative)

- **`GET /health`** — **liveness only** (process responds). **Does not** prove Postgres, migrations, ledger writes, or correct API key configuration.
- **`GET /ready`** — **operational readiness** (DB reachable, schema/migrations expectations met, ledger writable). **This** is what automation and operators should gate on before traffic or artefact-bound compliance.

### Required components / inputs

| Area | Requirement |
|------|----------------|
| **Postgres** | `DATABASE_URL` / `GOVAI_DATABASE_URL` reachable from the service; credentials correct |
| **Migrations** | Applied out-of-band or via `GOVAI_AUTO_MIGRATE=true` according to operator policy |
| **Ledger directory** | `GOVAI_LEDGER_DIR` set in staging/production; directory exists and is **writable** by the runtime user |
| **API keys (hosted)** | `GOVAI_API_KEYS_JSON` (map of bearer token → tenant id) non-empty JSON object in staging/prod |
| **Policy files** | Valid `policy.<env>.json` or `policy.json` under **`AIGOV_POLICY_DIR`** / cwd (or `AIGOV_POLICY_FILE`). Staging/prod **fail startup** when missing or invalid; dev may default unless **`AIGOV_POLICY_STRICT=true`** |

### Minimum healthy system checklist

- **`GET /ready` → 200** against the deployed base URL using a **real** operator or tenant key shape (not `/health`).
- **`GET /metrics` → 200** for Prometheus scraping (text exposition; no secrets in labels). Example: **`examples/observability/scrape-metrics.example.sh`**.
- Postgres: connect + `\dt` / migration version aligns with release notes.
- Ledger: persistence volume mounted; free space adequate; permission errors absent in logs.
- API keys: a smoke **`POST /evidence`** with a disposable `run_id` succeeds for a known-good key (**then** discard or isolate that run in non-prod).
- Evidence gates: **`submit-evidence-pack` → `verify-evidence-pack` → `govai check`** succeeds for a deterministic bundle when running the artefact-bound flow (see **`docs/golden-path.md`**).
- Runtime observability: events include `run_id`, `tenant_id`, `policy_id`, and `audit_trace_id`; validate local contracts with **`python3 scripts/observability_check.py`**. See **[`observability/runtime-telemetry-contract.md`](observability/runtime-telemetry-contract.md)** and **[`runtime/observability.md`](runtime/observability.md)**.

### System is **NOT** healthy if

- **`/ready` ≠ 200** while operators claim the environment is usable (treat as **infra not ready**, not INVALID/BLOCKED semantics).
- **DB unavailable**, migration mismatch, or read-only **`GOVAI_DATA_DIR`/ledger path** failures appear in logs.
- **Staging/prod audit** starts **without** resolvable **`GOVAI_API_KEYS_JSON`** or **policy** (**process should exit**).

CLI equivalents (preferred):

```bash
govai health
govai status
govai ready
```

## Startup checklist (env vars, DB, ledger, API keys)

Perform these checks before routing customer traffic or blaming CI.

### 1) Environment variables

Verify operator shell and runtime have the expected environment:

```bash
python3 - <<'PY'
import os
keys=[
  "GOVAI_AUDIT_BASE_URL",
  "GOVAI_API_KEY",
]
for k in keys:
  v=os.getenv(k)
  print(f"{k}:", "set" if v else "unset")
PY
```

At minimum, operator tooling requires:

- `GOVAI_AUDIT_BASE_URL`
- `GOVAI_API_KEY`

### 2) API reachability

```bash
govai health
```

If this fails, stop: this is an availability incident (DNS, routing, deployment down).

### 3) Shallow dependency status

```bash
govai status
```

If this fails, capture output and treat as an operator incident (misconfig, dependency down).

### 4) Readiness for evaluation

```bash
govai ready
```

If this fails while `status` succeeds, see “Common failure” below.

### 5) API key validity

If `health`/`status`/`ready` return 401, it is not a CI problem.

```bash
govai health
```

Fix by updating `GOVAI_API_KEY` to a valid token for the target base URL.

### 6) DB and ledger (operator responsibility)

Operator must confirm, from infrastructure telemetry/dashboards:

- DB is reachable from the API runtime (network + credentials).
- DB is at expected schema version (migrations applied).
- Ledger/event store is writable/readable (no permission or quota issues).

## Common failure: /status OK but /ready fails

Meaning: the API process is up and basic checks pass, but the system is not ready to evaluate end-to-end.

Most common causes:

- DB reachable but not initialized (migrations missing) or wrong database selected.
- Ledger/event store not writable (permissions, quota, wrong bucket/table).
- Required internal config not present at runtime (keys/URLs missing in the deployed environment).
- Cold start / initialization error that does not affect `/status` but prevents readiness.

What to do:

1) Confirm auth is not the issue:

```bash
govai health
```

2) Re-run readiness and capture output verbatim:

```bash
govai ready
```

3) Verify the deployed environment has the required config (not just your local shell).

4) Verify DB schema/migrations and ledger permissions in infra tooling.

5) If readiness still fails, escalate as an operator incident with:
   - environment (prod/preview/dev)
   - timestamp
   - `govai status` output
   - `govai ready` output

## What operator must verify before blaming CI

Before attributing a failing gate to CI:

- `govai health` succeeds against the CI target base URL.
- `govai status` succeeds.
- `govai ready` succeeds.
- CI is using the same `GOVAI_AUDIT_BASE_URL` and correct `GOVAI_API_KEY` for that environment.
- CI is using a stable `GOVAI_RUN_ID` across all evidence submit steps and the evaluation gate.
- Evidence submission steps are actually running (not skipped) and are pointing at the same API base URL.

If any of the above are false, it is an operator/config issue, not CI.

## What to request from customer

When a customer reports a failure, request the minimum set of facts needed to triage without back-and-forth:

- `GOVAI_AUDIT_BASE_URL` they are targeting
- `GOVAI_RUN_ID`
- Exact commands run and full output:
  - `govai health`
  - `govai status`
  - `govai ready`
  - `govai check --run-id "$GOVAI_RUN_ID"`
- Whether the failure is from local CLI or CI
- If CI: link to the CI run logs and confirmation that evidence steps ran

If they can share an export (when accessible):

```bash
govai export-run --run-id "$GOVAI_RUN_ID" > "govai-export-${GOVAI_RUN_ID}.json"
```
---
title: Operator runbook
audience: operators
scope: docs-only
---

## Purpose

This runbook is for operators running the GovAI audit service (hosted or self-hosted). It focuses on:

- startup readiness checks
- required environment variables
- Postgres connectivity and migrations
- ledger directory integrity and permissions
- API key configuration and tenant context
- safe rollback guidance
- meaning of `GET /health`, `GET /status`, `GET /ready`

For symptom-driven troubleshooting, see [troubleshooting.md](troubleshooting.md).

## Minimum healthy system

Minimum healthy system must satisfy:

- `GET /status` → `200`
- `GET /ready` → `200`
- database reachable and writable
- ledger directory writable
- API key accepted

Run:

```bash
curl -sS -i "https://<your-audit-base-url>/status"
curl -sS -i "https://<your-audit-base-url>/ready"
```

Notes:

- `/status` ≠ `/ready`. `/status` can be 200 while readiness is failing.
- `/ready` is required for CI success (digest/export/verdict checks depend on a ready backend).

## Startup checks (operator preflight)

Run these in order on a newly deployed instance.

### 1) Service endpoints respond

```bash
curl -sS -i "https://<your-audit-base-url>/health"
curl -sS -i "https://<your-audit-base-url>/status"
curl -sS -i "https://<your-audit-base-url>/ready"
```

Expected intent:

- `/health`: liveness only (should be 200 if the process is up).
- `/status`: informational, may be OK even if readiness is failing.
- `/ready`: operational readiness; **must** be 200 before taking traffic.

### 2) Postgres is reachable (from the service)

Operational readiness requires DB connectivity. Confirm the DB is reachable using the service’s configured `DATABASE_URL`.

If you have shell access in the running environment:

```bash
psql "$DATABASE_URL" -c "select 1;"
```

If you run via Docker Compose, verify the Postgres container is healthy and credentials match your `DATABASE_URL`.

### 3) Migrations are applied

GovAI is fail-fast: it should not accept traffic until migrations are in place. If `/ready` is not 200, treat it as a migrations/DB/ledger problem and inspect service logs.

Minimum operator expectation:

- migrations run automatically at startup (or as part of deploy)
- the migration user has privileges to create/alter required tables

### 4) Ledger directory exists and is writable

GovAI uses an append-only, hash-chained ledger on disk (the “ledger directory”). Readiness requires this directory to exist and be writable by the service user.

Operator checklist:

- mount is present (if containerized)
- filesystem is not read-only
- permissions allow create + fsync
- disk has enough free space

If ledger storage is ephemeral, you must understand the durability implications for your deployment profile.

## Required environment variables (operator surface)

The operator must provide at least:

- `DATABASE_URL`: Postgres connection string for the audit service.
- `GOVAI_API_KEYS_JSON`: API key → tenant mapping (the **tenant** is derived from the API key).

Commonly configured (depending on deployment):

- `GOVAI_LEDGER_DIR`: path to the ledger directory (must be writable).
- `RUST_LOG`: logging verbosity (e.g. `info` / `debug`).

Customer-visible (distributed to customers, not used for service boot):

- `GOVAI_AUDIT_BASE_URL`: the HTTPS base URL customers should use for CLI and the GitHub Action.
- `GOVAI_API_KEY`: per-tenant bearer token issued to customers.

## API key configuration and tenant context

### Tenant is derived from API key

GovAI’s ledger isolation is derived from the bearer API key mapping (server-side `GOVAI_API_KEYS_JSON`).

Important implications:

- If a customer uses the wrong API key, they may see `RUN_NOT_FOUND` for a run that exists in a different tenant.
- `X-GovAI-Project` / `GOVAI_PROJECT` are metadata/labels and **do not** determine ledger tenant.

### Operator tests for a newly issued key

After provisioning a new API key, do a minimal smoke check using a new run id:

```bash
export GOVAI_AUDIT_BASE_URL="https://<your-audit-base-url>"
export GOVAI_API_KEY="<newly-issued-key>"
export GOVAI_RUN_ID="$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"

python -m pip install --upgrade pip
python -m pip install "aigov-py==0.2.1"

export GOVAI_DEMO_RUN_ID="$GOVAI_RUN_ID"
govai run demo-deterministic
govai check --run-id "$GOVAI_RUN_ID"
govai export-run --run-id "$GOVAI_RUN_ID" > /tmp/govai-export.json
```

Expected: the deterministic demo transitions `BLOCKED → VALID`, and export succeeds.

## DB and migrations

Operational requirements:

- Postgres must be reachable with correct credentials.
- Migrations must be applied before readiness.

Troubleshooting heuristics:

- `/status` OK but `/ready` 503: usually DB/migrations/ledger.
- 5xx on customer endpoints: often DB connectivity flapping or a proxy mis-route; verify `/ready` and DB health first.

## Ledger directory

Operational requirements:

- the ledger directory must be writable
- the filesystem must preserve write ordering guarantees required by the service’s durability model
- backups/retention are operator concerns (append-only history can grow)

Common failure modes:

- wrong path mounted (points to an empty or read-only directory)
- permissions mismatch after deploy (container user changed)
- disk full causing readiness failures or runtime errors

## Safe rollback notes (operator guidance)

High-level safety principles:

- **Avoid rolling back across migrations** unless you have a tested downgrade plan.
- If you must roll back quickly, prefer:
  - deploying a previous build that is known to work with the current DB schema, or
  - restoring from a consistent snapshot (DB + ledger) if your incident process permits data rollback.

If your deploy process applies migrations automatically, treat schema changes as a one-way door unless you explicitly support downgrades.

## What the probes mean (`/health`, `/status`, `/ready`)

These endpoints are used by humans, load balancers, and orchestrators.

- `GET /health`
  - **Meaning**: liveness-only (process is up).
  - **Not a guarantee**: does not prove DB connectivity or ledger writability at the moment you call it.

- `GET /status`
  - **Meaning**: service status summary, useful for humans and dashboards.
  - **Not a guarantee**: can be OK even when readiness is failing.

- `GET /ready`
  - **Meaning**: authoritative operational readiness.
  - **Expectation**: only returns 200 when DB is reachable, required migrations are applied, and ledger storage is usable.
  - **Operational rule**: do not send production traffic until `/ready` is 200.
