from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _evidence_path(run_id: str) -> Path:
    return _repo_root() / "docs" / "evidence" / f"{run_id}.json"


def ensure_evidence_exists(run_id: str) -> Path:
    p = _evidence_path(run_id)
    if p.exists():
        return p
    p.parent.mkdir(parents=True, exist_ok=True)
    obj: Dict[str, Any] = {
        "run_id": run_id,
        "created_ts_utc": _utc_now_iso(),
        "events": [],
        "chain": {
            "algorithm": "event_hash_chain_v1",
            "head_sha256": None,
            "ts_utc": _utc_now_iso(),
        },
    }
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _base_event_for_hash(e: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(e.get("id") or ""),
        "type": str(e.get("type") or ""),
        "ts_utc": str(e.get("ts_utc") or ""),
        "actor": str(e.get("actor") or ""),
        "system": str(e.get("system") or ""),
        "run_id": str(e.get("run_id") or ""),
        "payload": e.get("payload"),
        "prev_sha256": e.get("prev_sha256"),
    }


def rebuild_chain_inplace(evidence: Dict[str, Any]) -> None:
    events = evidence.get("events")
    if not isinstance(events, list):
        events = []
        evidence["events"] = events

    prev: Optional[str] = None
    for e in events:
        if not isinstance(e, dict):
            continue
        e["prev_sha256"] = prev
        base = _base_event_for_hash(e)
        e["sha256"] = _sha256_bytes(_canonical_json(base))
        prev = e["sha256"]

    chain = evidence.get("chain")
    if not isinstance(chain, dict):
        chain = {}
        evidence["chain"] = chain
    chain["algorithm"] = "event_hash_chain_v1"
    chain["head_sha256"] = prev
    chain["ts_utc"] = _utc_now_iso()


def rebuild_chain_file(run_id: str) -> None:
    p = _evidence_path(run_id)
    if not p.exists():
        raise FileNotFoundError(f"Missing evidence file: {p}")
    evidence = _load_json(p)
    rebuild_chain_inplace(evidence)
    _atomic_write_json(p, evidence)


def emit_event(
    *,
    run_id: str,
    event_id: str,
    event_type: str,
    actor: str,
    system: str,
    payload: Dict[str, Any],
    ts_utc: Optional[str] = None,
) -> None:
    run_id = run_id.strip()
    if not run_id:
        raise ValueError("RUN_ID is required")

    if not event_id.strip():
        raise ValueError("event_id is required")

    p = ensure_evidence_exists(run_id)
    evidence = _load_json(p)

    events = evidence.get("events")
    if not isinstance(events, list):
        events = []
        evidence["events"] = events

    for e in events:
        if isinstance(e, dict) and e.get("id") == event_id:
            raise ValueError(f"duplicate event_id for run_id: event_id={event_id} run_id={run_id}")

    evt: Dict[str, Any] = {
        "id": event_id,
        "type": event_type,
        "ts_utc": ts_utc or _utc_now_iso(),
        "actor": actor,
        "system": system,
        "run_id": run_id,
        "payload": payload,
    }
    events.append(evt)

    rebuild_chain_inplace(evidence)
    _atomic_write_json(p, evidence)
