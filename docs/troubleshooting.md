# Troubleshooting

Goal: quickly diagnose a failing run and apply the smallest fix.

## Step 1: Identify failure type (ERROR vs BLOCKED vs INVALID)

Always start by obtaining the current verdict for the run:

```bash
export GOVAI_AUDIT_BASE_URL="https://api.example.com"
export GOVAI_API_KEY="YOUR_API_KEY"
export GOVAI_RUN_ID="YOUR_RUN_ID"

govai check --run-id "$GOVAI_RUN_ID"
```

Interpretation:

- `ERROR`: system/infra failure (timeout, digest mismatch, internal error)
- `BLOCKED`: evaluation cannot proceed due to missing/insufficient evidence
- `INVALID`: evaluation completed but failed policy rules (a real "fail")

If the CLI cannot fetch the run, first resolve `MISSING_API_KEY (401)` or `RUN_NOT_FOUND`.

## Runtime observability diagnostics

If dashboards or operator telemetry do not line up with audit evidence, validate the local observability package before changing runtime behavior:

```bash
python3 scripts/observability_check.py
```

Confirm every runtime event includes `run_id`, `tenant_id`, `policy_id`, and `audit_trace_id`. Use [`observability/incident-response.md`](observability/incident-response.md) for incident classification and [`runtime/observability.md`](runtime/observability.md) for the runtime-specific overview.

## MISSING_API_KEY (401)

Symptoms:

- `401 Unauthorized`
- `MISSING_API_KEY`
- `invalid token` / `missing bearer token`

Verify:

```bash
echo "${GOVAI_AUDIT_BASE_URL:-<unset>}"
python3 - <<'PY'
import os
print("GOVAI_API_KEY set:", bool(os.getenv("GOVAI_API_KEY")))
PY

# quick auth probe
govai health
```

Fix:

- Ensure `GOVAI_API_KEY` is set and not empty.
- Ensure the token is the correct environment (prod vs preview vs dev).
- If the token was rotated/revoked, obtain a fresh key and re-export it:

```bash
export GOVAI_API_KEY="NEW_KEY"
govai health
```

- If `govai health` still returns 401, confirm the base URL and that the API key matches that base URL’s tenant/project.

## RUN_NOT_FOUND

Symptoms:

- `RUN_NOT_FOUND`
- `404 Not Found` when checking/exporting a run

Verify:

```bash
echo "$GOVAI_RUN_ID"
govai check --run-id "$GOVAI_RUN_ID"
```

Common causes:

- Wrong `GOVAI_RUN_ID` (typo, different UUID, using CI run id instead of GovAI run id)
- Wrong `GOVAI_AUDIT_BASE_URL` (pointing at another environment)
- Evidence was submitted under a different run id

Fix:

- Recompute or retrieve the intended `GOVAI_RUN_ID` used by the workflow that submitted evidence.
- Confirm you are pointing to the same environment that received evidence:

```bash
echo "$GOVAI_AUDIT_BASE_URL"
```

- If the run truly does not exist, re-run the workflow that creates/submits evidence for that `GOVAI_RUN_ID`.

## ERROR (infra/digest/timeout)

Symptoms:

- Verdict shows `ERROR`
- CLI prints timeouts, transient HTTP errors, or "digest" / "hash" mismatch

Verify:

```bash
govai health
govai status
govai check --run-id "$GOVAI_RUN_ID"
```

If `health` fails, this is not a run-specific issue.

Fix:

- **Transient network/timeouts**: retry with a clean shell and stable network; avoid parallel job storms.
- **Service unhealthy** (`health` fails): stop—this is an operator incident. Escalate with timestamp, base URL, and error output.
- **Digest mismatch** (evidence payload integrity mismatch):
  - Ensure evidence submission code did not transform the payload after hashing (no JSON re-serialization differences, no whitespace/key-order changes if hashing raw text).
  - Re-submit the evidence exactly as produced (same bytes) under the same `GOVAI_RUN_ID`.
  - If evidence is generated from artifacts, ensure the artifact content is stable (pin dependencies, avoid non-deterministic build steps).

## BLOCKED (missing evidence)

Symptoms:

- Verdict shows `BLOCKED`
- Output includes `missing evidence:` entries

Verify:

```bash
govai check --run-id "$GOVAI_RUN_ID"
```

Fix:

- Submit the missing evidence types for the same `GOVAI_RUN_ID`.
- Re-run the evidence-producing job(s) ensuring they publish evidence events to the API tied to `GOVAI_AUDIT_BASE_URL`.
- Confirm the evidence was associated with the correct run id:
  - The evidence submitter must use exactly the same `GOVAI_RUN_ID` used by the gate.

Operational rule:

- Do not treat `BLOCKED` as a pass/fail. It indicates incomplete inputs. The fix is always: provide the missing evidence or change the workflow to produce it.

## INVALID (evaluation failure)

Symptoms:

- Verdict shows `INVALID`
- Output indicates a policy/evaluation failure

Verify:

```bash
govai check --run-id "$GOVAI_RUN_ID"
govai export-run --run-id "$GOVAI_RUN_ID" > "govai-export-${GOVAI_RUN_ID}.json"
python3 - <<'PY'
import json,sys
obj=json.load(open(sys.argv[1]))
print("verdict:", obj.get("verdict"))
PY "govai-export-${GOVAI_RUN_ID}.json"
```

Fix:

- Treat `INVALID` as a real gate failure:
  - Fix the underlying compliance issue in the system under evaluation.
  - Or adjust the evidence generation so it reflects the actual controls (only if evidence was wrong/incomplete, not to "game" the evaluation).
- Re-run the workflow to produce new evidence and a new run id (or the same run id if your process supports it), then re-check.

Escalation checklist (include in ticket/slack message):

- `GOVAI_AUDIT_BASE_URL`
- `GOVAI_RUN_ID`
- `govai health` output
- `govai status` output
- `govai check --run-id ...` output
# GovAI troubleshooting

## Step 1: Identify failure type

Run:

```bash
govai check --run-id "$GOVAI_RUN_ID"
