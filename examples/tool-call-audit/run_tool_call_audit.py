#!/usr/bin/env python3
"""Agent tool-call evidence linked to a final AI decision (reconstructible export)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "examples/reference-runtime-common"))

from flow import (  # noqa: E402
    client_from_env,
    env_config,
    execute_guard,
    post_evidence_dict,
    print_json,
    read_run,
    require_api_key,
)
from lifecycle import discovery  # noqa: E402


def build_events(run_id: str) -> list[dict]:
    tool_call_id = f"{run_id}-tool-search"
    tool_result_id = f"{run_id}-tool-result"
    decision_id = f"{run_id}-decision"
    return [
        discovery(run_id),
        {
            "event_id": tool_call_id,
            "event_type": "tool_call",
            "ts_utc": "2026-01-01T00:00:20Z",
            "actor": "tool-call-audit",
            "system": "aigov-core-examples",
            "run_id": run_id,
            "payload": {
                "tool_name": "search_knowledge_base",
                "input_hash": "in-tool-001",
                "agent_id": "planner-agent",
            },
        },
        {
            "event_id": tool_result_id,
            "event_type": "tool_output",
            "ts_utc": "2026-01-01T00:00:21Z",
            "actor": "tool-call-audit",
            "system": "aigov-core-examples",
            "run_id": run_id,
            "payload": {
                "tool_name": "search_knowledge_base",
                "output_hash": "out-tool-001",
                "tool_call_event_id": tool_call_id,
                "result_preview": "3 matching policy clauses",
            },
        },
        {
            "event_id": decision_id,
            "event_type": "ai_decision_completed",
            "ts_utc": "2026-01-01T00:00:22Z",
            "actor": "tool-call-audit",
            "system": "aigov-core-examples",
            "run_id": run_id,
            "payload": {
                "decision": "approve_with_citations",
                "tool_evidence_refs": [tool_call_id, tool_result_id],
                "summary": "Decision grounded in tool outputs",
            },
        },
    ]


def main() -> None:
    cfg = env_config()
    run_id = str(cfg["run_id"])
    print("Tool-call AIGov Core reference.")
    print(f"base_url={cfg['base']} run_id={run_id}")

    events = build_events(run_id)
    for ev in events:
        print(f"  - {ev['event_type']} ({ev['event_id']})")

    if not execute_guard():
        return

    api_key = require_api_key()
    client = client_from_env()
    timeout = float(cfg["timeout"])

    for ev in events:
        print(f"\n-> POST /evidence ({ev['event_type']})")
        body = post_evidence_dict(client, ev, timeout=timeout)
        print(json.dumps(body, indent=2))

    summary, export, verify = read_run(
        base=str(cfg["base"]),
        api_key=api_key,
        run_id=run_id,
        project=cfg["project"],
        timeout=timeout,
    )
    print_json("GET /compliance-summary", summary)
    print_json("GET /api/export/{run_id}", export)
    print_json("GET /verify", verify)

    events_in_export = export.get("evidence_events") or []
    types = {e.get("event_type") for e in events_in_export if isinstance(e, dict)}
    if "tool_call" not in types or "tool_output" not in types:
        raise RuntimeError(f"export missing tool evidence; event types seen: {sorted(types)}")

    if verify.get("ok") is not True:
        raise RuntimeError(f"verify failed: {verify}")

    print("\nExport should list tool_call and tool_output for reconstructible tool use.")


if __name__ == "__main__":
    main()
