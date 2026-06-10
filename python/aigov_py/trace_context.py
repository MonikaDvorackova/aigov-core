"""W3C Trace Context helpers for linking GovAI evidence to external traces (no OTel SDK required)."""

from __future__ import annotations

import re
from typing import Any

_TRACEPARENT_RE = re.compile(
    r"^00-(?P<trace_id>[0-9a-fA-F]{32})-(?P<span_id>[0-9a-fA-F]{16})-(?P<flags>[0-9a-fA-F]{2})$"
)


def parse_traceparent(value: str | None) -> dict[str, str] | None:
    """Parse W3C ``traceparent`` header value into trace/span identifiers."""

    if not value or not str(value).strip():
        return None
    m = _TRACEPARENT_RE.match(str(value).strip())
    if not m:
        return None
    return {
        "trace_id": m.group("trace_id").lower(),
        "span_id": m.group("span_id").lower(),
        "trace_flags": m.group("flags").lower(),
        "propagation": "w3c_traceparent",
    }


def external_trace_payload(traceparent: str | None) -> dict[str, Any] | None:
    """Build optional ``payload.external_trace`` object for evidence ingest."""

    parsed = parse_traceparent(traceparent)
    if not parsed:
        return None
    return parsed


def attach_external_trace(payload: dict[str, Any], traceparent: str | None) -> dict[str, Any]:
    """Return a copy of ``payload`` with ``external_trace`` when ``traceparent`` is valid."""

    out = dict(payload)
    ext = external_trace_payload(traceparent)
    if ext:
        out["external_trace"] = ext
    return out
