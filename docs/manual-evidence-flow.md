# Manual evidence flow (advanced)

This document shows how to manually submit GovAI evidence events without using the deterministic demo.

## Prereqs

Set the same env vars used everywhere else:

```bash
export GOVAI_AUDIT_BASE_URL="https://api.example.com"
export GOVAI_API_KEY="YOUR_API_KEY"
export GOVAI_RUN_ID="YOUR_RUN_ID"
```

GovAI expects **one** `GOVAI_RUN_ID` to be used end-to-end: evidence submission → `govai check` → `govai export-run`.

## Event sequence (what each event means)

Submit these events **for the same** `GOVAI_RUN_ID`, in order:

### 1) `data_registered`

Registers dataset identity + governance commitment.

### 2) `model_trained`

Ties a model version to the run (and to the dataset).

### 3) `evaluation_reported`

Reports an evaluation result. Policies typically require `"passed": true` to proceed.

### 4) `risk_recorded`

Creates a risk record for the assessment.

### 5) `risk_mitigated`

Records mitigation status and narrative.

### 6) `risk_reviewed`

Captures a reviewer decision (commonly `"approve"`).

### 7) `human_approved`

Captures a named approval for a scope (in this flow: `"scope": "model_promoted"`).

### 8) `model_promoted`

Records promotion intent; policies typically accept this only after prerequisites are satisfied.

## Human Approval Gate (`human_approved`)

Human approval is a **critical compliance gate** in GovAI. Many policies require explicit human sign-off before a model can be promoted to production.

### Why Human Approval Matters
Even if all technical evidence (data registration, training, evaluation, risk review) is complete, the compliance verdict will remain **`BLOCKED`** until a proper `human_approved` event is recorded for the `model_promoted` scope.

### Required Fields for `human_approved`

```json
{
  "event_type": "human_approved",
  "run_id": "YOUR_RUN_ID",
  "payload": {
    "scope": "model_promoted",
    "decision": "approve",
    "approved": true,
    "approver": "compliance_officer@example.com",
    "justification": "Reviewed evaluation results, risk assessment, and mitigation plan. All criteria satisfied.",
    "ai_system_id": "expense-ai",
    "model_version_id": "...",
    "assessment_id": "...",
    "risk_id": "..."
  }
}
```
### Related Commands & Examples

- Use the dedicated approve CLI: `python -m aigov_py.approve ...`
- See `python -m aigov_py.approve --help` for all options
- Full end-to-end example is available in `docs/golden-path.md`
- For CI usage, see `docs/github-action.md`

## Copy/paste: submit the full sequence via `POST /evidence`

This script submits the full sequence above to `POST $GOVAI_AUDIT_BASE_URL/evidence`.

```bash
python3 - <<'PY'
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

base = os.environ["GOVAI_AUDIT_BASE_URL"].rstrip("/")
api_key = os.environ["GOVAI_API_KEY"]
run_id = os.environ["GOVAI_RUN_ID"]

def utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def post_evidence(ev: dict) -> None:
    req = urllib.request.Request(
        url=f"{base}/evidence",
        method="POST",
        data=json.dumps(ev).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", "replace")
            if resp.status < 200 or resp.status >= 300:
                raise RuntimeError(f"POST /evidence failed: {resp.status} {body}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"POST /evidence failed: {e.code} {body}") from None

ai_system_id = "expense-ai"
dataset_id = "expense_dataset_v1"
dataset_commitment = "basic_compliance"

model_version_id = f"mv_{run_id}"
assessment_id = f"asmt_{run_id}"
risk_id = f"risk_{run_id}"
human_event_id = f"manual_human_approved_{run_id}"
artifact_path = f"artifacts/model_{run_id}.joblib"

events = [
    {
        "event_id": f"manual_data_registered_{run_id}",
        "event_type": "data_registered",
        "ts_utc": utc_now_z(),
        "actor": "manual_flow",
        "system": "manual_flow",
        "run_id": run_id,
        "payload": {
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "dataset": "customer_expense_records",
            "dataset_version": "v1",
            "dataset_fingerprint": "sha256:demo",
            "dataset_governance_id": "gov_expense_v1",
            "dataset_governance_commitment": dataset_commitment,
            "source": "internal",
            "intended_use": "expense classification",
            "limitations": "demo dataset",
            "quality_summary": "validated sample",
            "governance_status": "registered",
        },
    },
    {
        "event_id": f"manual_model_trained_{run_id}",
        "event_type": "model_trained",
        "ts_utc": utc_now_z(),
        "actor": "manual_flow",
        "system": "manual_flow",
        "run_id": run_id,
        "payload": {
            "model_version_id": model_version_id,
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_type": "LogisticRegression",
            "artifact_path": artifact_path,
            "artifact_sha256": "manual_flow_placeholder",
        },
    },
    {
        "event_id": f"manual_evaluation_reported_{run_id}",
        "event_type": "evaluation_reported",
        "ts_utc": utc_now_z(),
        "actor": "manual_flow",
        "system": "manual_flow",
        "run_id": run_id,
        "payload": {
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
            "metric": "accuracy",
            "value": 0.95,
            "threshold": 0.8,
            "passed": True,
        },
    },
    {
        "event_id": f"manual_risk_recorded_{run_id}",
        "event_type": "risk_recorded",
        "ts_utc": utc_now_z(),
        "actor": "manual_flow",
        "system": "manual_flow",
        "run_id": run_id,
        "payload": {
            "assessment_id": assessment_id,
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
            "risk_id": risk_id,
            "risk_class": "high",
            "severity": 4.0,
            "likelihood": 0.3,
            "status": "submitted",
            "mitigation": "Establish evaluation threshold and require human promotion approval.",
            "owner": "risk_owner",
            "dataset_governance_commitment": dataset_commitment,
        },
    },
    {
        "event_id": f"manual_risk_mitigated_{run_id}",
        "event_type": "risk_mitigated",
        "ts_utc": utc_now_z(),
        "actor": "manual_flow",
        "system": "manual_flow",
        "run_id": run_id,
        "payload": {
            "assessment_id": assessment_id,
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
            "risk_id": risk_id,
            "status": "mitigated",
            "mitigation": "Mitigation applied: restrict intended use to governed demo scope + enforce passed evaluation gate.",
            "dataset_governance_commitment": dataset_commitment,
        },
    },
    {
        "event_id": f"manual_risk_reviewed_{run_id}",
        "event_type": "risk_reviewed",
        "ts_utc": utc_now_z(),
        "actor": "manual_flow",
        "system": "manual_flow",
        "run_id": run_id,
        "payload": {
            "assessment_id": assessment_id,
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
            "risk_id": risk_id,
            "decision": "approve",
            "reviewer": "risk_officer",
            "justification": "Reviewed in manual flow; approve risk mitigation.",
            "dataset_governance_commitment": dataset_commitment,
        },
    },
    {
        "event_id": human_event_id,
        "event_type": "human_approved",
        "ts_utc": utc_now_z(),
        "actor": "manual_flow",
        "system": "manual_flow",
        "run_id": run_id,
        "payload": {
            "scope": "model_promoted",
            "decision": "approve",
            "approved": True,
            "approver": "compliance_officer",
            "justification": "Manual approval after evaluation + risk review.",
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
            "assessment_id": assessment_id,
            "risk_id": risk_id,
            "dataset_governance_commitment": dataset_commitment,
        },
    },
    {
        "event_id": f"manual_model_promoted_{run_id}",
        "event_type": "model_promoted",
        "ts_utc": utc_now_z(),
        "actor": "manual_flow",
        "system": "manual_flow",
        "run_id": run_id,
        "payload": {
            "artifact_path": artifact_path,
            "promotion_reason": "approved_by_human",
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
            "assessment_id": assessment_id,
            "risk_id": risk_id,
            "dataset_governance_commitment": dataset_commitment,
            "approved_human_event_id": human_event_id,
        },
    },
]

for ev in events:
    post_evidence(ev)

print("ok")
PY
```

