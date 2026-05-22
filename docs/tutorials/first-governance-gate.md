# Tutorial: First governance gate

## Audience

An engineer wiring GovAI into CI for the first time.

## Prerequisites

- Repository clone of GovAI or a customer repo using the **`govai`** CLI.
- Python **3.10+** and the **`python/.venv`** setup from [`../project/local_development.md`](../project/local_development.md).

## Steps

1. **Install the CLI** (from `python/` with venv activated):

   ```bash
   cd python && source .venv/bin/activate && pip install -e ".[dev]" && cd ..
   ```

2. **Point to your audit base URL** (local Compose example):

   ```bash
   export GOVAI_AUDIT_BASE_URL=http://127.0.0.1:8088
   export GOVAI_API_KEY=test-key
   ```

3. **Run a check** for an existing `run_id` (after evidence exists):

   ```bash
   govai check --run-id "$RUN_ID"
   ```

## Expected outputs

- Exit code **0** when the service returns **`VALID`** for the run (per your policy and data).
- Exit code **3** for **`BLOCKED`** in fail-closed demos — see **`examples/blocked_deployment.sh`**.

## Common failures

| Symptom | Likely cause |
| --- | --- |
| Connection refused | Audit service not listening on **`GOVAI_AUDIT_BASE_URL`** |
| 401 / 403 | **`GOVAI_API_KEY`** mismatch vs server configuration |
| Unexpected verdict | Missing evidence or approvals — inspect **`GET /compliance-summary`** JSON |

## Screenshot slot

- Capture your CI log showing **`govai check`** with a clear verdict line (redact secrets).

## Teaching narrative

The gate exists to ensure **no green merge** without a **machine-checkable** story that evidence and approvals support the decision.
