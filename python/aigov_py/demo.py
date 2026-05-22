import subprocess
import json
import os
from datetime import datetime, timezone

from .prototype_domain import (
    approved_human_event_id_for_run,
    dataset_governance_iris,
    model_version_id_for_run,
    risk_lifecycle_payloads,
)

API = "http://127.0.0.1:8088/evidence"


def _now_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _post(event: dict) -> None:
    subprocess.run(
        [
            "curl",
            "-sS",
            "-X",
            "POST",
            API,
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(event),
        ],
        check=False,
    )


def main() -> None:
    run_id = os.environ.get("RUN_ID", "").strip()
    if not run_id:
        raise SystemExit("RUN_ID is required")

    actor = "monika"
    system = "aigov_poc"

    dataset_gov = dataset_governance_iris()
    ai_system_id = dataset_gov["ai_system_id"]
    dataset_id = dataset_gov["dataset_id"]
    model_version_id = model_version_id_for_run(run_id)
    risk_recorded_payload, _, _ = risk_lifecycle_payloads(run_id)
    assessment_id = risk_recorded_payload["assessment_id"]
    risk_id = risk_recorded_payload["risk_id"]
    dataset_commitment = risk_recorded_payload["dataset_governance_commitment"]

    ts1 = _now_ts()
    approve = {
        "event_id": approved_human_event_id_for_run(run_id),
        "event_type": "human_approved",
        "ts_utc": ts1,
        "actor": actor,
        "system": system,
        "run_id": run_id,
        "payload": {
            "scope": "model_promoted",
            "decision": "approve",
            "approver": "compliance_officer",
            "justification": "metrics meet threshold and dataset fingerprint verified",
            "assessment_id": assessment_id,
            "risk_id": risk_id,
            "dataset_governance_commitment": dataset_commitment,
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
        },
    }

    _post(approve)

    ts2 = _now_ts()
    promote = {
        "event_id": f"mp_after_approval_{run_id}",
        "event_type": "model_promoted",
        "ts_utc": ts2,
        "actor": actor,
        "system": system,
        "run_id": run_id,
        "payload": {
            "artifact_path": f"python/artifacts/model_{run_id}.joblib",
            "promotion_reason": "approved_by_human",
            "artifact_sha256": None,
            "assessment_id": assessment_id,
            "risk_id": risk_id,
            "dataset_governance_commitment": dataset_commitment,
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
            "approved_human_event_id": approved_human_event_id_for_run(run_id),
        },
    }

    _post(promote)

    print(f"ok run_id={run_id}")
    print(f"next: make bundle RUN_ID={run_id}")


if __name__ == "__main__":
    main()
