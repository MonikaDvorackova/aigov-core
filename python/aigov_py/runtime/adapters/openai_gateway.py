"""OpenAI-style gateway metadata helpers (no ``openai`` import).

Use these keys inside ``EvidenceEvent.payload`` or side-channel logs; the audit
service still validates ``event_type`` and payload per deployed policy.
"""

from __future__ import annotations

from typing import Any, Mapping


def gateway_request_metadata(
    *,
    route_id: str,
    upstream_model: str,
    correlation_id: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Stable dict for embedding gateway routing context into evidence payloads."""
    out: dict[str, Any] = {
        "gateway_route_id": route_id,
        "upstream_model": upstream_model,
        "correlation_id": correlation_id,
    }
    if extra:
        out.update(dict(extra))
    return out


def merge_payload(base: Mapping[str, Any], extension: Mapping[str, Any]) -> dict[str, Any]:
    """Shallow merge (``extension`` wins on key collision) for deterministic merges."""
    merged: dict[str, Any] = dict(base)
    merged.update(dict(extension))
    return merged
