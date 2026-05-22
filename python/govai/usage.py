from __future__ import annotations

from typing import Any

from .client import GovAIClient, GovAIHTTPError


def _normalize_usage(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Normalized usage response shape across server modes.

    Server modes:
    - metering=off: legacy per-tenant evidence counter + limit.
    - metering=on: team-based monthly counters + plan limits.
    """
    metering = payload.get("metering")
    metering = metering if isinstance(metering, str) else None

    # Always preserve the full, unmodified server payload (lossless).
    out: dict[str, Any] = {"raw": payload}

    # Provide a stable top-level wrapper without dropping any information.
    out["ok"] = payload.get("ok", True) if isinstance(payload.get("ok"), bool) else True
    out["metering"] = metering

    # metering=off (legacy evidence quota)
    if metering == "off":
        out["tenant_id"] = payload.get("tenant_id")
        out["period_start"] = payload.get("period_start")
        out["evidence_events_count"] = payload.get("evidence_events_count")
        out["limit"] = payload.get("limit")
        return out

    # metering=on (team telemetry + plan limits)
    if metering == "on":
        out["team_id"] = payload.get("team_id")
        out["year_month"] = payload.get("year_month")
        out["plan"] = payload.get("plan")
        out["new_run_ids"] = payload.get("new_run_ids")
        out["evidence_events"] = payload.get("evidence_events")
        out["limits"] = payload.get("limits")
        return out

    # Unknown/extended shape: still lossless via out["raw"].
    return out


def get_usage(client: GovAIClient, *, project: str | None = None) -> dict[str, Any]:
    """
    ``GET /usage`` — usage + limits.

    Notes:
    - Requires audit API auth (Bearer token) on the Rust server.
    - If ``project`` is set, passes it as ``X-GovAI-Project`` (legacy metering scope).
    - Returns a normalized dict with the original response available under ``raw`` if unknown.
    """
    headers = None
    if project is not None and project.strip():
        headers = {"X-GovAI-Project": project.strip()}

    data = client.request_json("GET", "/usage", headers=headers, raise_on_body_ok_false=False)
    if not isinstance(data, dict):
        raise GovAIHTTPError(f"expected object from /usage, got {type(data).__name__}")
    return _normalize_usage(data)

