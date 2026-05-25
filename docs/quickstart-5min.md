# Local developer quickstart (≤5 minutes)

If you are integrating with a hosted GovAI backend, start here instead (canonical):

- [customer-onboarding-10min.md](customer-onboarding-10min.md)

Goal: create an API key, send your first evidence event, run a compliance check, and interpret the result.

This guide uses the **core v1 HTTP API** (`api/govai-http-v1.openapi.yaml`) and the shipped **`govai` CLI** (`python/aigov_py/cli.py`).

```docs
preset: cli-catalog
```

```flow
preset: evidence
```

```demo
demo: evidence
```

## Prereqs

- Rust toolchain
- Python ≥ 3.10
- Writable directory for the ledger (`GOVAI_LEDGER_DIR`)
- PostgreSQL is **optional** (only needed for issued API keys in Postgres or `GET /ready` DB checks)

## 0) Install the CLI (local editable)

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd ..
govai --version
```

## 1) Create an API key (shared secret)

GovAI audit API keys are **configured on the audit service** via `GOVAI_API_KEYS` (comma-separated). When set, audit routes require `Authorization: Bearer <secret>`.

**Note (local/dev vs hosted):**
This quickstart uses `GOVAI_API_KEYS` for simple local/dev setups. **Hosted / staging / production deployments MUST define `GOVAI_API_KEYS_JSON`** so each API key is mapped to a tenant id and ledger isolation is enforced correctly. **Dev mode without API keys is not suitable for pilots**: hosted pilots must run with real key → tenant mapping.

- Ledger tenant isolation is derived from the **API key → tenant mapping** (not from request headers).
- `X-GovAI-Project` is optional metadata (usage/billing label) and **does not** isolate ledger tenant.

Generate a local key:

```bash
export GOVAI_API_KEY="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
```

## 2) Start the audit runtime with that key

```bash
export GOVAI_LEDGER_DIR="$(pwd)/.govai-ledger"
mkdir -p "$GOVAI_LEDGER_DIR"
export GOVAI_API_KEYS="$GOVAI_API_KEY"
export GOVAI_API_KEYS_JSON="{\"$GOVAI_API_KEY\":\"local-dev\"}"
export AIGOV_ENVIRONMENT=dev
export AIGOV_POLICY_DIR="$(pwd)/rust"

# In one terminal:
make run-audit

# In another:
curl -sS http://127.0.0.1:8088/status
curl -sS http://127.0.0.1:8088/health
```

## 3) Send your first evidence event (HTTP)

Pick a `run_id` (`GOVAI_RUN_ID`), then append one `data_registered` event.

```steps
title: Register evidence for a new run
steps:
  - label: Set run_id
    command: |
      export GOVAI_RUN_ID="$(python3 - <<'PY'
      import uuid
      print(uuid.uuid4())
      PY
      )"
  - label: Set event_id
    command: |
      export EVENT_ID="$(python3 - <<'PY'
      import uuid
      print(uuid.uuid4())
      PY
      )"
  - label: POST evidence
    command: |
      curl -sS http://127.0.0.1:8088/evidence \
        -H "content-type: application/json" \
        -H "authorization: Bearer $GOVAI_API_KEY" \
        -d "$(python3 - <<PY
      import json, os
      from datetime import datetime, timezone
      print(json.dumps({
        "event_id": os.environ["EVENT_ID"],
        "event_type": "data_registered",
        "ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "actor": "quickstart",
        "system": "quickstart",
        "run_id": os.environ["GOVAI_RUN_ID"],
        "payload": {
          "ai_system_id": "expense-ai",
          "dataset_id": "expense_dataset_v1",
          "dataset": "customer_expense_records",
          "dataset_version": "v1",
          "dataset_fingerprint": "sha256:demo",
          "dataset_governance_id": "gov_expense_v1",
          "dataset_governance_commitment": "basic_compliance",
          "source": "internal",
          "intended_use": "expense classification",
          "limitations": "demo dataset",
          "quality_summary": "validated sample",
          "governance_status": "registered",
        },
      }))
      PY
      )"
    expected: '{"ok":true,"record_hash":"...","policy_version":"...","environment":"..."}'
```

## 4) Run a compliance check (HTTP + CLI)

> [!summary]
> After one evidence event, `compliance-summary` should return **BLOCKED** until the full promotion sequence is recorded.

```steps
title: Read the authoritative decision
steps:
  - label: HTTP compliance-summary
    explain: Query the immutable ledger verdict for your run_id using your API key.
    command: |
      curl -sS "http://127.0.0.1:8088/compliance-summary?run_id=$GOVAI_RUN_ID" \
        -H "authorization: Bearer $GOVAI_API_KEY"
    expected: '{"verdict":"BLOCKED",...}'
  - label: CLI gate check
    explain: The CLI prints the verdict and exits non-zero when the run is not VALID.
    command: |
      govai check --audit-base-url "http://127.0.0.1:8088" --api-key "$GOVAI_API_KEY" --run-id "$GOVAI_RUN_ID"
      echo $?
    expected: stdout BLOCKED; exit code 2
```

At this point (only 1 event), the expected verdict is **`BLOCKED`**.

- The server only returns `VALID` when **evaluation passed**, **risk reviewed (approve)**, **human approved (approve)**, and **promotion executed** for the run.
- With only `data_registered`, those prerequisites are missing, so the run is intentionally **blocked**.

### Get a full end-to-end VALID run (CLI)

The fastest path to a complete, policy-satisfying sequence is the built-in scripted demo flow.

```bash
export GOVAI_AUDIT_BASE_URL="http://127.0.0.1:8088"
export GOVAI_API_KEY="$GOVAI_API_KEY"

govai run demo
```

Expected stdout:

```text
VALID
```

Note: `govai run demo` generates its **own** `run_id` internally. It is a separate path from the API-only steps above (which use your `$GOVAI_RUN_ID`).

## Optional: minimal VALID evidence sequence (API-only)

If you want to reach `VALID` **using only the HTTP API**, append the remaining required evidence for the same `$GOVAI_RUN_ID` (in this order):

1. `model_trained`
2. `evaluation_reported` (with `"passed": true`)
3. `risk_recorded`
4. `risk_mitigated`
5. `risk_reviewed` (with `"decision": "approve"`)
6. `human_approved` (with `"scope":"model_promoted"` and `"decision":"approve"`)
7. `model_promoted`

Copy/paste (uses deterministic IDs derived from `$GOVAI_RUN_ID`):

```bash
export MODEL_VERSION_ID="mv_$GOVAI_RUN_ID"
export ASSESSMENT_ID="asmt_$GOVAI_RUN_ID"
export RISK_ID="risk_$GOVAI_RUN_ID"
export ARTIFACT_PATH="python/artifacts/model_${GOVAI_RUN_ID}.joblib"

post_ev () {
  local event_type="$1"
  python3 - "$event_type" <<'PY' | curl -sS http://127.0.0.1:8088/evidence \
    -H "content-type: application/json" \
    -H "authorization: Bearer $GOVAI_API_KEY" \
    -d @-
import json, os, sys
from datetime import datetime, timezone
event_type = sys.argv[1]
run_id = os.environ["GOVAI_RUN_ID"]
now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def base(payload):
  return {
    "event_id": f"qs_{event_type}_{run_id}",
    "event_type": event_type,
    "ts_utc": now,
    "actor": "quickstart",
    "system": "quickstart",
    "run_id": run_id,
    "payload": payload,
  }

ai_system_id = "expense-ai"
dataset_id = "expense_dataset_v1"
model_version_id = os.environ["MODEL_VERSION_ID"]
assessment_id = os.environ["ASSESSMENT_ID"]
risk_id = os.environ["RISK_ID"]
artifact_path = os.environ["ARTIFACT_PATH"]
commitment = "basic_compliance"

payloads = {
  "model_trained": {
    "ai_system_id": ai_system_id,
    "dataset_id": dataset_id,
    "model_version_id": model_version_id,
    "model_type": "LogisticRegression",
    "artifact_path": artifact_path,
    "artifact_sha256": "quickstart_placeholder",
  },
  "evaluation_reported": {
    "ai_system_id": ai_system_id,
    "dataset_id": dataset_id,
    "model_version_id": model_version_id,
    "metric": "accuracy",
    "value": 0.95,
    "threshold": 0.8,
    "passed": True,
  },
  "risk_recorded": {
    "assessment_id": assessment_id,
    "ai_system_id": ai_system_id,
    "dataset_id": dataset_id,
    "model_version_id": model_version_id,
    "risk_id": risk_id,
    "risk_class": "high",
    "severity": 4.0,
    "likelihood": 0.3,
    "status": "submitted",
    "mitigation": "Require passed evaluation + human approval before promotion.",
    "owner": "risk_owner",
    "dataset_governance_commitment": commitment,
  },
  "risk_mitigated": {
    "assessment_id": assessment_id,
    "ai_system_id": ai_system_id,
    "dataset_id": dataset_id,
    "model_version_id": model_version_id,
    "risk_id": risk_id,
    "status": "mitigated",
    "mitigation": "Mitigation applied: evaluation threshold + human approval gate.",
    "dataset_governance_commitment": commitment,
  },
  "risk_reviewed": {
    "assessment_id": assessment_id,
    "ai_system_id": ai_system_id,
    "dataset_id": dataset_id,
    "model_version_id": model_version_id,
    "risk_id": risk_id,
    "decision": "approve",
    "reviewer": "risk_officer",
    "justification": "Reviewed in quickstart; approve risk mitigation.",
    "dataset_governance_commitment": commitment,
  },
  "human_approved": {
    "scope": "model_promoted",
    "decision": "approve",
    "approved": True,
    "approver": "compliance_officer",
    "justification": "Quickstart approval after evaluation + risk review.",
    "ai_system_id": ai_system_id,
    "dataset_id": dataset_id,
    "model_version_id": model_version_id,
    "assessment_id": assessment_id,
    "risk_id": risk_id,
    "dataset_governance_commitment": commitment,
  },
  "model_promoted": {
    "artifact_path": artifact_path,
    "promotion_reason": "approved_by_human",
    "ai_system_id": ai_system_id,
    "dataset_id": dataset_id,
    "model_version_id": model_version_id,
    "assessment_id": assessment_id,
    "risk_id": risk_id,
    "dataset_governance_commitment": commitment,
    "approved_human_event_id": f"qs_human_approved_{run_id}",
  },
}

print(json.dumps(base(payloads[event_type])))
PY
}

post_ev model_trained
post_ev evaluation_reported
post_ev risk_recorded
post_ev risk_mitigated
post_ev risk_reviewed
post_ev human_approved
post_ev model_promoted
```

Now the expected verdict is `VALID`:

```bash
curl -sS "http://127.0.0.1:8088/compliance-summary?run_id=$GOVAI_RUN_ID" \
  -H "authorization: Bearer $GOVAI_API_KEY"

govai check --audit-base-url "http://127.0.0.1:8088" --api-key "$GOVAI_API_KEY" --run-id "$GOVAI_RUN_ID"
echo $?
```

Expected:

- `GET /compliance-summary`: `"verdict":"VALID"`
- `govai check`: stdout `VALID`, exit code `0`

## 5) Interpret the result

`GET /compliance-summary` returns:

- **`verdict`**: one of `VALID`, `INVALID`, `BLOCKED`
- **`current_state`**: the projected state derived from the evidence log
- **`policy_version`** and **deployment `environment`** metadata

Minimal, machine-friendly check (exit code 0 only if `VALID`):

```bash
govai check --audit-base-url "http://127.0.0.1:8088" --api-key "$GOVAI_API_KEY" --run-id "$GOVAI_RUN_ID"
```

## 6) Export the run (machine-readable JSON)

Use the dedicated export endpoint to fetch a **stable JSON document** that includes:

- **decision** extracts (evaluation / approval / promotion)
- **hashes** (canonical bundle SHA-256 + append-only chain hashes)

CLI:

```bash
govai export-run \
  --audit-base-url "http://127.0.0.1:8088" \
  --api-key "$GOVAI_API_KEY" \
  --run-id "$GOVAI_RUN_ID"
```

HTTP:

```bash
curl -sS "http://127.0.0.1:8088/api/export/$GOVAI_RUN_ID" \
  -H "authorization: Bearer $GOVAI_API_KEY"
```

## Appendix: single-line compliance summary (CLI)

```bash
govai compliance-summary \
  --audit-base-url "http://127.0.0.1:8088" \
  --api-key "$GOVAI_API_KEY" \
  --run-id "$GOVAI_RUN_ID" \
  --compact-json
```

