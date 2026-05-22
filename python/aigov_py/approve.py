from __future__ import annotations

import json
import os
import uuid
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict
from .prototype_domain import (
    approved_human_event_id_for_run,
    dataset_governance_iris,
    risk_lifecycle_payloads,
)


def _post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    headers = {"Content-Type": "application/json"}

    api_key = os.environ.get("GOVAI_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    project = os.environ.get("GOVAI_PROJECT", "").strip()
    if project:
        headers["X-GovAI-Project"] = project

    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _eid(prefix: str, run_id: str) -> str:
    return f"{prefix}_{run_id}_{uuid.uuid4()}"


def main() -> None:
    run_id = os.environ.get("RUN_ID", "").strip()
    if not run_id:
        raise SystemExit("RUN_ID is required")

    actor = os.getenv("AIGOV_ACTOR", "monika")
    system = os.getenv("AIGOV_SYSTEM", "aigov_poc")

    endpoint = (
        os.getenv("GOVAI_AUDIT_BASE_URL") or os.getenv("AIGOV_AUDIT_ENDPOINT") or os.getenv("AIGOV_AUDIT_URL") or "http://127.0.0.1:8088"
    ).rstrip("/")
    url = f"{endpoint}/evidence"

    ts_utc = _utc_now_iso()
    remote_event_id = approved_human_event_id_for_run(run_id)

    dataset_gov = dataset_governance_iris()
    dataset_commitment = dataset_gov["dataset_governance_commitment"]
    risk_recorded_payload, _, _ = risk_lifecycle_payloads(run_id)
    assessment_id = risk_recorded_payload["assessment_id"]
    risk_id = risk_recorded_payload["risk_id"]
    model_version_id = risk_recorded_payload["model_version_id"]
    ai_system_id = risk_recorded_payload["ai_system_id"]
    dataset_id = risk_recorded_payload["dataset_id"]

    event: Dict[str, Any] = {
        "event_id": remote_event_id,
        "event_type": "human_approved",
        "ts_utc": ts_utc,
        "actor": actor,
        "system": system,
        "run_id": run_id,
        "payload": {
            "scope": "model_promoted",
            "decision": "approve",
            "approver": "compliance_officer",
            "justification": "metrics meet threshold and dataset governance commitment verified",
            "assessment_id": assessment_id,
            "risk_id": risk_id,
            "dataset_governance_commitment": dataset_commitment,
          "ai_system_id": ai_system_id,
          "dataset_id": dataset_id,
          "model_version_id": model_version_id,
        },
    }

    try:
        out = _post_json(url, event)
    except Exception:
        raise

    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
