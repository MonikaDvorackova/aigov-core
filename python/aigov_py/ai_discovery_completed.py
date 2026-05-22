from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict


def _utc_now_iso() -> str:
    return "1970-01-01T00:00:00Z"


def _post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # The ledger rejects duplicate event_id for a run_id with HTTP 409.
        # Treat this as an idempotent retry: desired evidence is already present.
        if int(getattr(e, "code", 0) or 0) == 409:
            return {"ok": True, "idempotent": True, "status_code": 409}
        raise


def main() -> None:
    run_id = (os.environ.get("RUN_ID") or "").strip()
    if not run_id:
        raise SystemExit("RUN_ID is required")

    actor = (os.environ.get("AIGOV_ACTOR") or "local_flow").strip() or "local_flow"
    system = (os.environ.get("AIGOV_SYSTEM") or "aigov_poc").strip() or "aigov_poc"

    endpoint = (
        os.getenv("AIGOV_AUDIT_ENDPOINT")
        or os.getenv("AIGOV_AUDIT_URL")
        or os.getenv("GOVAI_AUDIT_BASE_URL")
        or "http://127.0.0.1:8088"
    ).rstrip("/")
    url = f"{endpoint}/evidence"

    event_id = f"ai_discovery_completed_{run_id}"

    # Important: the Rust projection satisfies requirement `ai_discovery_completed`
    # when it sees event_type `ai_discovery_reported`.
    payload = {
        "status": "completed",
        # Signals used by the compliance projection:
        "openai": False,
        "transformers": False,
        "model_artifacts": False,
        # Extra structured fields for audit reconstruction:
        "openai_detected": False,
        "transformers_detected": False,
        "model_artifacts_detected": False,
        "source": "local_flow",
        "notes": "no AI discovery findings in deterministic local flow",
    }

    ev: Dict[str, Any] = {
        "event_id": event_id,
        "event_type": "ai_discovery_reported",
        "ts_utc": _utc_now_iso(),
        "actor": actor,
        "system": system,
        "run_id": run_id,
        "payload": payload,
    }

    out = _post_json(url, ev)
    if not isinstance(out, dict) or not out.get("ok"):
        raise SystemExit(f"ai_discovery_completed emission failed: {out}")

    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()

