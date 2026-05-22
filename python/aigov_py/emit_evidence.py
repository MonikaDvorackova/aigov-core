import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import requests


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def emit(
    endpoint: str,
    event_type: str,
    actor: str,
    system: str,
    run_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "ts_utc": utc_now(),
        "actor": actor,
        "system": system,
        "run_id": run_id,
        "payload": payload,
    }
    r = requests.post(endpoint, json=event, timeout=10)
    r.raise_for_status()
    return r.json()
