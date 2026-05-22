from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Mapping

from govai import GovAIAPIError, GovAIClient, GovAIHTTPError, submit_event

_DUPLICATE_EVENT_RAW_RE = re.compile(
    r"duplicate event_id for run_id:\s*event_id=([^\s]+)\s+run_id=([^\s]+)",
    re.IGNORECASE,
)

_DUPLICATE_EVENT_ID_CODE = "DUPLICATE_EVENT_ID"


def canonicalize_evidence_event_dicts(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mirrors Rust `canonicalize_evidence_events` for dict payloads."""

    sorted_e = sorted(events, key=lambda e: str(e.get("ts_utc") or ""))
    seen: set[str] = set()
    out_rev: list[dict[str, Any]] = []

    for e in reversed(sorted_e):
        eid = str(e.get("event_id") or "")
        if eid and eid not in seen:
            seen.add(eid)
            out_rev.append(e)

    out_rev.reverse()
    out_rev.sort(
        key=lambda e: (
            str(e.get("ts_utc") or ""),
            str(e.get("event_type") or ""),
            str(e.get("event_id") or ""),
        ),
    )
    return out_rev


def event_for_submit(ev: Mapping[str, Any]) -> dict[str, Any]:
    """POST body matches CI-generated evidence; omit server-stamped `environment`."""

    body = dict(ev)
    body.pop("environment", None)
    return body


def _error_code_from_response_json(payload: dict[str, Any]) -> str | None:
    err = payload.get("error")
    if isinstance(err, dict):
        c = err.get("code")
        if isinstance(c, str) and c.strip():
            return c.strip().upper()

    c2 = payload.get("code")
    if isinstance(c2, str) and c2.strip():
        return c2.strip().upper()

    return None


def _duplicate_event_run_from_error_payload(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (event_id, run_id) from DUPLICATE_EVENT_ID details/message if present."""

    err = payload.get("error")
    detail_sources: list[Mapping[str, Any]] = []

    if isinstance(err, dict):
        detail_sources.append(err)

    detail_sources.append(payload)

    for source in detail_sources:
        det = source.get("details")
        if isinstance(det, dict):
            raw = det.get("raw")
            if isinstance(raw, str):
                m = _DUPLICATE_EVENT_RAW_RE.search(raw)
                if m:
                    return m.group(1), m.group(2)

            eid = det.get("event_id")
            rid = det.get("run_id")
            if isinstance(eid, str) and eid.strip() and isinstance(rid, str) and rid.strip():
                return eid.strip(), rid.strip()

        msg = source.get("message")
        if isinstance(msg, str) and msg:
            m = _DUPLICATE_EVENT_RAW_RE.search(msg)
            if m:
                return m.group(1), m.group(2)

    return None, None


def is_duplicate_event_id_idempotent_acceptance(
    status_code: int,
    response_body_text: str,
    submitted: Mapping[str, Any],
) -> bool:
    """True only for duplicate event conflict on the same event_id/run_id."""

    if int(status_code or 0) != 409:
        return False

    text = (response_body_text or "").strip()
    if not text:
        return False

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return False

    if not isinstance(payload, dict):
        return False

    if _error_code_from_response_json(payload) != _DUPLICATE_EVENT_ID_CODE:
        return False

    duplicate_event_id, duplicate_run_id = _duplicate_event_run_from_error_payload(payload)
    if not duplicate_event_id or not duplicate_run_id:
        return False

    expected_event_id = str(submitted.get("event_id") or "")
    expected_run_id = str(submitted.get("run_id") or "")

    return duplicate_event_id == expected_event_id and duplicate_run_id == expected_run_id


def _http_error_body_text(exc: GovAIHTTPError) -> str:
    body_text = getattr(exc, "body_text", None)
    if isinstance(body_text, str):
        return body_text

    payload = getattr(exc, "payload", None)
    if isinstance(payload, dict):
        return json.dumps(payload, sort_keys=True)

    return ""


def _is_idempotent_duplicate_409_for_body(exc: GovAIHTTPError, submitted: Mapping[str, Any]) -> bool:
    return is_duplicate_event_id_idempotent_acceptance(
        int(getattr(exc, "status_code", 0) or 0),
        _http_error_body_text(exc),
        submitted,
    )


def submit_event_or_idempotent_duplicate(client: GovAIClient, body: dict[str, Any]) -> None:
    """
    POST /evidence for one event; treat DUPLICATE_EVENT_ID as success only when
    the conflict names the same event_id and run_id as this request body.
    """

    try:
        submit_event(client, body)
    except GovAIHTTPError as e:
        if _is_idempotent_duplicate_409_for_body(e, body):
            print(f"already submitted: {str(body.get('event_id') or '')}")
            return
        raise


def load_bundle(run_id: str, artifact_dir: Path) -> tuple[dict[str, Any], Path]:
    p = artifact_dir / f"{run_id}.json"
    if not p.is_file():
        raise FileNotFoundError(f"missing evidence bundle JSON: {p}")

    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"expected object in {p}, got {type(data).__name__}")

    return data, p


def load_manifest(artifact_dir: Path) -> dict[str, Any]:
    p = artifact_dir / "evidence_digest_manifest.json"
    if not p.is_file():
        raise FileNotFoundError(f"missing digest manifest {p}")

    ob = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(ob, dict):
        raise TypeError("manifest must be a JSON object")

    return ob


def submit_evidence_bundle_events(
    client: GovAIClient,
    *,
    bundle: Mapping[str, Any],
    progress: Callable[[int, int, str], None] | None = None,
) -> None:
    evs = bundle.get("events")
    if not isinstance(evs, list):
        raise ValueError("bundle.events must be an array")

    decoded: list[dict[str, Any]] = []
    for i, e in enumerate(evs):
        if not isinstance(e, dict):
            raise TypeError(f"bundle.events[{i}] must be an object")
        decoded.append(dict(e))

    ordered = canonicalize_evidence_event_dicts(decoded)
    n = len(ordered)

    required = frozenset({"event_id", "event_type", "ts_utc", "actor", "system", "run_id", "payload"})

    for idx, raw in enumerate(ordered, start=1):
        missing = sorted(required.difference(raw.keys()))
        if missing:
            raise ValueError(f"event[{idx}] missing keys: {', '.join(missing)}")

        if not isinstance(raw.get("payload"), dict):
            raise TypeError(f"event[{idx}].payload must be an object")

        body = event_for_submit(raw)
        event_type = str(body.get("event_type") or "")

        if progress is not None:
            progress(idx, n, event_type)

        submit_event_or_idempotent_duplicate(client, body)


def bundle_hash_digest(client: GovAIClient, run_id: str) -> dict[str, Any]:
    raw = client.request_json(
        "GET",
        "/bundle-hash",
        params={"run_id": run_id},
        raise_on_body_ok_false=True,
    )

    if not isinstance(raw, dict):
        raise TypeError(f"/bundle-hash: expected dict, got {type(raw).__name__}")

    digest = raw.get("events_content_sha256")
    if not isinstance(digest, str) or len(digest.strip()) != 64:
        raise GovAIAPIError(
            "/bundle-hash missing events_content_sha256 "
            "(artifact-bound gate requires GovAI audit >= this revision; refusal is intentional).",
            raw,
        )

    return raw


def fetch_export_evidence_hashes(client: GovAIClient, run_id: str) -> tuple[dict[str, Any] | None, str | None]:
    """GET /api/export/:run_id → evidence_hashes. Returns (dict, None) or (None, skip_reason)."""

    try:
        raw = client.request_json(
            "GET",
            f"/api/export/{run_id}",
            raise_on_body_ok_false=True,
        )
    except Exception:
        return None, "export not available"

    if not isinstance(raw, dict):
        return None, "export response was not a JSON object"

    eh = raw.get("evidence_hashes")
    if not isinstance(eh, dict):
        return None, "export response missing evidence_hashes"

    return eh, None
