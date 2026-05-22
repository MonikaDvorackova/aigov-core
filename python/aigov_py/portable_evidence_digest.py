"""
Portable evidence digest (``aigov.evidence_digest.v1``) aligned with Rust
``bundle::portable_evidence_digest_v1`` for offline artifact checks.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from aigov_py.evidence_artifact_gate import canonicalize_evidence_event_dicts


def sort_json_value(obj: Any) -> Any:
    """Recursive key sort matching Rust ``bundle::sort_json_value``."""

    if isinstance(obj, dict):
        return {k: sort_json_value(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [sort_json_value(x) for x in obj]
    return obj


def portable_evidence_digest_v1(run_id: str, events: list[dict[str, Any]]) -> str:
    """
    SHA-256 hex over canonical JSON:
    ``{"schema":"aigov.evidence_digest.v1","run_id":...,"events":[...]}``
    where each event omits ``environment`` (server stamp), matching production.
    """

    rid = run_id.strip()
    decoded = [dict(e) for e in events]
    ordered = canonicalize_evidence_event_dicts(decoded)
    ev_values: list[Any] = []
    for raw in ordered:
        stripped = {k: v for k, v in raw.items() if k != "environment"}
        ev_values.append(sort_json_value(stripped))

    envelope = sort_json_value(
        {
            "schema": "aigov.evidence_digest.v1",
            "run_id": rid,
            "events": ev_values,
        }
    )
    body = json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
