from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
from typing import Any, Dict, List


def now_utc_iso() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def repo_root_from_file() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", ".."))


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_json(path: str, payload: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def stable_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_minimal_evidence(run_id: str, mode: str) -> Dict[str, Any]:
    ts = now_utc_iso()

    genesis = {
        "id": "genesis",
        "event_id": "genesis",
        "event_type": "evidence_genesis",
        "run_id": run_id,
        "ts_utc": ts,
        "type": "evidence_genesis",
        "actor": "ci_fallback",
        "system": "ci_fallback",
        "payload": {"source": "ci_fallback"},
        "prev_event_id": None,
    }

    head = {
        "id": "ci_fallback_used",
        "event_id": "ci_fallback_used",
        "event_type": "ci_fallback_used",
        "run_id": run_id,
        "ts_utc": ts,
        "type": "ci_fallback_used",
        "actor": "ci_fallback",
        "system": "ci_fallback",
        "payload": {"source": "ci_fallback"},
        "prev_event_id": "genesis",
    }

    events: List[Dict[str, Any]] = [genesis, head]

    for e in events:
        e["hash"] = stable_hash(e)

    return {
        "run_id": run_id,
        "ts_utc": ts,
        "kind": "evidence",
        "system": "ci_fallback",
        "mode": mode,
        "policy_version": "v0.4_ci",
        "events": events,
        "chain": {
            "head": head["id"],
            "hash_alg": "sha256",
        },
        "chain_head": head["id"],
        "meta": {
            "aigov_mode": mode,
            "source": "ci_fallback",
            "warning": "CI fallback evidence. Forbidden in PROD.",
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python ci_fallback.py <run_id>", file=sys.stderr)
        return 2

    run_id = argv[1].strip()
    if not run_id:
        return 2

    mode = os.environ.get("AIGOV_MODE", "ci")
    if mode == "prod":
        print("ci_fallback is forbidden in PROD", file=sys.stderr)
        return 2

    root = repo_root_from_file()
    out_dir = os.path.join(root, "docs", "evidence")
    ensure_dir(out_dir)

    payload = build_minimal_evidence(run_id, mode)
    path = os.path.join(out_dir, f"{run_id}.json")
    write_json(path, payload)
    print(f"saved {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
