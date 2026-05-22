from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

from .events import emit_event
from .prototype_domain import dataset_governance_iris, model_version_id_for_run


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _eid(prefix: str, run_id: str) -> str:
    return f"{prefix}_{run_id}_{uuid.uuid4()}"


def _env_float(name: str) -> Optional[float]:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    try:
        return float(raw)
    except ValueError as e:
        raise SystemExit(f"{name} must be a number, got: {raw!r}") from e


def main() -> None:
    run_id = (os.environ.get("RUN_ID") or "").strip()
    if not run_id:
        raise SystemExit("RUN_ID is required")

    actor = (os.getenv("AIGOV_ACTOR", "monika") or "monika").strip() or "monika"
    system = (os.getenv("AIGOV_SYSTEM", "aigov_poc") or "aigov_poc").strip() or "aigov_poc"
    dataset_gov = dataset_governance_iris()
    ai_system_id = dataset_gov["ai_system_id"]
    dataset_id = dataset_gov["dataset_id"]
    model_version_id = model_version_id_for_run(run_id)

    endpoint = (os.getenv("AIGOV_AUDIT_ENDPOINT", "http://127.0.0.1:8088") or "").rstrip("/")
    url = f"{endpoint}/evidence"

    metric = (os.getenv("AIGOV_EVAL_METRIC", "f1") or "f1").strip() or "f1"
    value = _env_float("AIGOV_EVAL_VALUE")
    threshold = _env_float("AIGOV_EVAL_THRESHOLD")

    if value is None:
        raise SystemExit("AIGOV_EVAL_VALUE is required (e.g. 0.88)")
    if threshold is None:
        raise SystemExit("AIGOV_EVAL_THRESHOLD is required (e.g. 0.85)")

    passed = value >= threshold
    ts = _utc_now_iso()

    remote_event_id = _eid("eval", run_id)

    remote_event: Dict[str, Any] = {
        "event_id": remote_event_id,
        "event_type": "evaluation_reported",
        "ts_utc": ts,
        "actor": actor,
        "system": system,
        "run_id": run_id,
        "payload": {
            "evaluation_attempt_id": str(uuid.uuid4()),
            "metric": metric,
            "value": value,
            "threshold": threshold,
            "passed": passed,
            "remote_event_id": f"evaluation_{run_id}_{remote_event_id}",
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
        },
    }

    emit_event(
        run_id=run_id,
        event_type="evaluation_started",
        actor=actor,
        payload={"ts_utc": ts, "remote_event_id": remote_event_id, "metric": metric},
        system=system,
        event_id=_eid("evaluation_started", run_id),
    )

    try:
        r = requests.post(url, json=remote_event, timeout=10)
        resp_text = r.text
        status_code = r.status_code
    except Exception as e:
        emit_event(
            run_id=run_id,
            event_type="evaluation_failed",
            actor=actor,
            payload={"ts_utc": ts, "remote_event_id": remote_event_id, "error": str(e)},
            system=system,
            event_id=_eid("evaluation_failed", run_id),
        )
        raise

    emit_event(
        run_id=run_id,
        event_type="evaluation_reported",
        actor=actor,
        payload={
            "ts_utc": ts,
            "remote_event_id": remote_event_id,
            "http_status": status_code,
            "response_text": resp_text,
            "metric": metric,
            "value": value,
            "threshold": threshold,
            "passed": passed,
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
        },
        system=system,
        event_id=_eid("evaluation_reported", run_id),
    )

    print(resp_text)

    ok = False
    try:
        parsed = json.loads(resp_text)
        if isinstance(parsed, dict):
            ok = bool(parsed.get("ok", False))
    except json.JSONDecodeError:
        ok = 200 <= status_code < 300

    if not ok:
        raise SystemExit(1)

    # Optional: fail locally if the metric didn't pass (keeps CLI semantics strict)
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
