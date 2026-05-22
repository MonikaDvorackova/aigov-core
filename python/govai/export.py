from __future__ import annotations

from typing import Any

from .client import GovAIClient, GovAIHTTPError


def export_run(client: GovAIClient, run_id: str, *, project: str | None = None) -> dict[str, Any]:
    """
    ``GET /api/export/:run_id`` — machine-readable audit export.

    Notes:
    - Requires audit API auth (Bearer token) on the Rust server.
    - Ledger tenant is derived from API key mapping on the server; ``project`` does **not** select the ledger.
    - If ``project`` is set, passes it as ``X-GovAI-Project`` for metering / metadata only.
    - Returns the raw JSON object (including ``ok: false`` error objects).
    """
    rid = (run_id or "").strip()
    if not rid:
        raise ValueError("run_id is required")

    headers = None
    if project is not None and project.strip():
        headers = {"X-GovAI-Project": project.strip()}

    data = client.request_json(
        "GET",
        f"/api/export/{rid}",
        headers=headers,
        raise_on_body_ok_false=False,
    )
    if not isinstance(data, dict):
        raise GovAIHTTPError(f"expected object from /api/export/:run_id, got {type(data).__name__}")
    return data

