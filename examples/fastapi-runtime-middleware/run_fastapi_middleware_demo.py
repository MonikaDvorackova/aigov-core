#!/usr/bin/env python3
"""Minimal FastAPI app: middleware records GovAI evidence for each AI decision."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "python"))
sys.path.insert(0, str(_ROOT / "examples/reference-runtime-common"))

from flow import client_from_env, env_config, execute_guard, post_evidence_dict, print_json  # noqa: E402
from lifecycle import discovery  # noqa: E402


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_decision_trace(client, run_id: str, *, decision_id: str, timeout: float) -> None:
    """Simulate middleware hooks: request → decision started → completed."""
    events = [
        {
            "event_id": f"{decision_id}-request",
            "event_type": "http_request_received",
            "ts_utc": utc_now(),
            "actor": "fastapi-middleware",
            "system": "govai-core-examples",
            "run_id": run_id,
            "payload": {"path": "/ai/decide", "method": "POST", "decision_id": decision_id},
        },
        {**discovery(run_id), "event_id": f"{decision_id}-discovery"},
        {
            "event_id": f"{decision_id}-ai-started",
            "event_type": "ai_decision_started",
            "ts_utc": utc_now(),
            "actor": "fastapi-middleware",
            "system": "govai-core-examples",
            "run_id": run_id,
            "payload": {"decision_id": decision_id, "model": "mock-router"},
        },
        {
            "event_id": f"{decision_id}-completed",
            "event_type": "ai_decision_completed",
            "ts_utc": utc_now(),
            "actor": "fastapi-middleware",
            "system": "govai-core-examples",
            "run_id": run_id,
            "payload": {
                "decision_id": decision_id,
                "outcome": "allow",
                "summary": "mock decision completed",
            },
        },
    ]
    for ev in events:
        print(f"-> POST /evidence ({ev['event_type']})")
        print(json.dumps(post_evidence_dict(client, ev, timeout=timeout), indent=2))


def main() -> None:
    cfg = env_config()
    run_id = str(cfg["run_id"])
    print("FastAPI middleware reference (in-process simulation; optional HTTP server below).")
    print(f"base_url={cfg['base']} run_id={run_id}")

    if not execute_guard():
        print("\nOptional server: pip install 'aigov-py[server]' && python3 examples/fastapi-runtime-middleware/app.py")
        return

    client = client_from_env()
    record_decision_trace(client, run_id, decision_id=f"{run_id}-dec-1", timeout=float(cfg["timeout"]))

    summary = client.get_compliance_summary(run_id, timeout_sec=float(cfg["timeout"]))
    print_json("GET /compliance-summary (logged by middleware)", dict(summary.raw))


if __name__ == "__main__":
    main()
