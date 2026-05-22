from __future__ import annotations

from typing import Any

from .client import GovAIClient


def get_compliance_summary(
    client: GovAIClient, run_id: str, *, timeout: float = 30.0
) -> dict[str, Any]:
    """
    ``GET /compliance-summary?run_id=...``

    Returns the full JSON object (including ``ok: false`` when the run cannot be loaded).
    """
    return client.request_json(
        "GET",
        "/compliance-summary",
        params={"run_id": run_id},
        raise_on_body_ok_false=False,
        timeout=timeout,
    )
