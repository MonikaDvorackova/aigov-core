#!/usr/bin/env python3
"""Reconstructible agent demo: append-only evidence → export → offline replay viewer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_DEMO = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "examples/reference-runtime-common"))

from flow import (  # noqa: E402
    client_from_env,
    env_config,
    execute_guard,
    get_json,
    post_evidence_dict,
    print_json,
    read_run,
    require_api_key,
    auth_headers,
    _join,
)
from lifecycle import (  # noqa: E402
    data_registered,
    discovery,
    evaluation_reported,
    human_approved,
    model_promoted,
    model_trained,
    risk_recorded,
    risk_reviewed,
)

# Mocked agent I/O (no external LLM API).
MOCK_USER_REQUEST = "Should we approve deploying the retention-policy assistant to production?"
MOCK_REASONING = (
    "Query policy corpus via search_knowledge_base; require human sign-off before promotion."
)
MOCK_TOOL_RESULT = "3 matching policy clauses; deployment requires compliance officer approval."


def _base(run_id: str, event_id: str, event_type: str, ts: str, payload: dict) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "ts_utc": ts,
        "actor": "reconstructible-agent-demo",
        "system": "aigov-core-examples",
        "run_id": run_id,
        "payload": payload,
    }


def agent_trace_events(run_id: str) -> list[dict]:
    tool_call_id = f"{run_id}-tool-call"
    tool_output_id = f"{run_id}-tool-output"
    return [
        _base(
            run_id,
            f"{run_id}-user-request",
            "user_request",
            "2026-05-01T10:00:00Z",
            {
                "channel": "operator-console",
                "request_text": MOCK_USER_REQUEST,
                "session_id": f"{run_id}-session",
            },
        ),
        _base(
            run_id,
            f"{run_id}-model-reasoning",
            "model_reasoning",
            "2026-05-01T10:00:01Z",
            {
                "agent_id": "govai-planner",
                "step": "plan",
                "reasoning_preview": MOCK_REASONING,
                "linked_event_ids": [f"{run_id}-user-request"],
            },
        ),
        _base(
            run_id,
            tool_call_id,
            "tool_call",
            "2026-05-01T10:00:02Z",
            {
                "tool_name": "search_knowledge_base",
                "input_hash": "in-recon-demo-001",
                "agent_id": "govai-planner",
                "linked_event_ids": [f"{run_id}-model-reasoning"],
            },
        ),
        _base(
            run_id,
            tool_output_id,
            "tool_output",
            "2026-05-01T10:00:03Z",
            {
                "tool_name": "search_knowledge_base",
                "output_hash": "out-recon-demo-001",
                "tool_call_event_id": tool_call_id,
                "result_preview": MOCK_TOOL_RESULT,
            },
        ),
        _base(
            run_id,
            f"{run_id}-policy-eval",
            "policy_evaluation",
            "2026-05-01T10:00:04Z",
            {
                "policy_id": "govai.runtime.agent-tool-use.dev",
                "outcome": "allow",
                "reason_codes": ["TOOL_USE_ALLOWED"],
                "linked_event_ids": [tool_output_id],
            },
        ),
    ]


def governance_events(run_id: str) -> list[dict]:
    """Ledger lifecycle evidence for evaluation, risk, approval, and promotion gates."""
    return [
        discovery(run_id),
        data_registered(run_id),
        model_trained(run_id),
        evaluation_reported(run_id, passed=True),
        risk_recorded(run_id),
        risk_reviewed(run_id),
    ]


def final_decision_event(run_id: str) -> dict:
    return _base(
        run_id,
        f"{run_id}-decision",
        "ai_decision_completed",
        "2026-05-01T10:00:08Z",
        {
            "decision": "approve_with_human_gate",
            "summary": "Deploy after human_approved and model_promoted evidence",
            "tool_evidence_refs": [f"{run_id}-tool-call", f"{run_id}-tool-output"],
            "policy_evaluation_event_id": f"{run_id}-policy-eval",
        },
    )


def approval_and_promotion(run_id: str) -> list[dict]:
    human = human_approved(run_id)
    human["actor"] = "reconstructible-agent-demo"
    human["system"] = "aigov-core-examples"
    human["ts_utc"] = "2026-05-01T10:00:09Z"
    promote = model_promoted(run_id)
    promote["actor"] = "reconstructible-agent-demo"
    promote["system"] = "aigov-core-examples"
    promote["ts_utc"] = "2026-05-01T10:00:10Z"
    return [human, promote]


def verdict_from_summary(summary: dict) -> str:
    return str(summary.get("verdict") or summary.get("compliance_verdict") or "UNKNOWN")


def save_export(run_id: str, export: dict) -> Path:
    out_dir = _DEMO / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run_id}.json"
    path.write_text(json.dumps(export, indent=2) + "\n", encoding="utf-8")
    return path


def print_plan(run_id: str) -> None:
    steps = [
        "1. User request",
        "2. Model reasoning step",
        "3. Tool call",
        "4. Tool output",
        "5. Policy evaluation",
        "6. Governance lifecycle (evaluation + risk)",
        "7. Final decision (ai_decision_completed)",
        "8. Compliance summary (expect BLOCKED — human approval required)",
        "9. Human approval granted",
        "10. Model promoted",
        "11. Compliance summary (ledger-authoritative verdict)",
        "12. Audit export download → exports/<run_id>.json",
        "13. Verify endpoint",
        "14. Open viewer/index.html with saved export",
    ]
    print("Reconstructible agent demo (AIGov Core runtime routes only).")
    print(f"base_url={env_config()['base']} run_id={run_id}")
    print("\nSimulated lifecycle:")
    for line in steps:
        print(f"  {line}")
    print("\nMocked components: user prompt, model reasoning text, tool result (no OpenAI/API).")
    print("Live components: POST /evidence, GET /compliance-summary, GET /api/export, GET /verify.")


def main() -> None:
    cfg = env_config()
    run_id = str(cfg["run_id"])
    print_plan(run_id)

    trace = agent_trace_events(run_id)
    gov = governance_events(run_id)
    decision = final_decision_event(run_id)
    post_approval = approval_and_promotion(run_id)

    all_planned = trace + gov + [decision] + post_approval
    print(f"\nPlanned evidence events ({len(all_planned)}):")
    for ev in all_planned:
        print(f"  - {ev['event_type']} ({ev['event_id']})")

    if not execute_guard():
        print("\nDry run complete. Set GOVAI_EXAMPLE_EXECUTE=1 with a running aigov_audit.")
        return

    api_key = require_api_key()
    client = client_from_env()
    timeout = float(cfg["timeout"])
    base = str(cfg["base"])

    def ingest(ev: dict, label: str) -> None:
        print(f"\n-> POST /evidence — {label} ({ev['event_type']})")
        body = post_evidence_dict(client, ev, timeout=timeout)
        print(json.dumps(body, indent=2))
        if body.get("ok") is not True:
            raise RuntimeError(f"ingest failed: {body}")

    for ev in trace:
        ingest(ev, "agent trace")
    for ev in gov:
        ingest(ev, "governance")
    ingest(decision, "final decision")

    summary_blocked, _, _ = read_run(
        base=base,
        api_key=api_key,
        run_id=run_id,
        project=cfg["project"],
        timeout=timeout,
    )
    print_json("GET /compliance-summary (human approval required)", summary_blocked)
    blocked_verdict = verdict_from_summary(summary_blocked)
    print(f"ledger_verdict_before_approval={blocked_verdict}")
    if blocked_verdict not in ("BLOCKED", "INVALID"):
        print(
            "Note: expected BLOCKED before human_approved; continuing to append approval evidence.",
            file=sys.stderr,
        )

    for ev in post_approval:
        ingest(ev, "approval gate")

    summary_final, export, verify = read_run(
        base=base,
        api_key=api_key,
        run_id=run_id,
        project=cfg["project"],
        timeout=timeout,
    )
    print_json("GET /compliance-summary (final)", summary_final)
    print_json("GET /api/export/{run_id}", export)
    print_json("GET /verify/{run_id}", verify)

    final_verdict = verdict_from_summary(summary_final)
    export_verdict = (export.get("decision") or {}).get("verdict")
    print(f"ledger_verdict_final={final_verdict}")
    print(f"export_decision_verdict={export_verdict}")

    if final_verdict != export_verdict:
        raise RuntimeError(
            f"compliance-summary verdict {final_verdict!r} != export decision.verdict {export_verdict!r}"
        )

    if verify.get("ok") is not True:
        raise RuntimeError(f"verify failed: {verify}")

    export_path = save_export(run_id, export)
    viewer = _DEMO / "viewer" / "index.html"
    print(f"\nExport saved: {export_path}")
    print(f"Replay viewer: file://{viewer.resolve()}")
    print("Load the export JSON in the viewer (file picker or ?export=../exports/<run_id>.json).")

    headers = auth_headers(api_key, cfg["project"])
    bundle_hash = get_json(_join(base, f"/bundle-hash/{run_id}"), headers, timeout)
    print_json("GET /bundle-hash/{run_id} (hash continuity)", bundle_hash)
    chain = (export.get("evidence_hashes") or {}).get("log_chain") or []
    if not chain:
        raise RuntimeError("export missing evidence_hashes.log_chain for replay integrity display")

    event_types = {e.get("event_type") for e in export.get("evidence_events") or [] if isinstance(e, dict)}
    for required in ("tool_call", "tool_output", "policy_evaluation", "human_approved"):
        if required not in event_types:
            raise RuntimeError(f"export missing {required}; types={sorted(event_types)}")

    if final_verdict != "VALID":
        raise RuntimeError(
            f"expected VALID after full lifecycle; got {final_verdict!r} — check policy and evidence order"
        )

    print("\nDemo complete: append-only evidence, deterministic export, chain verify OK.")


if __name__ == "__main__":
    main()
