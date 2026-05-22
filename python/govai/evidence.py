from __future__ import annotations

from typing import Any

from .client import GovAIClient


def submit_event(client: GovAIClient, event: dict[str, Any]) -> dict[str, Any]:
    """
    POST ``/evidence`` with a single evidence event payload.

    Returns the JSON object from a successful ingest (includes ``ok``, ``record_hash``, etc.).
    """
    data = client.request_json(
        "POST",
        "/evidence",
        json_body=event,
        raise_on_body_ok_false=True,
    )
    if not isinstance(data, dict):
        raise TypeError(f"expected dict from /evidence, got {type(data).__name__}")
    return data
