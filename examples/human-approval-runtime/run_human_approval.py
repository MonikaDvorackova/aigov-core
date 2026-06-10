#!/usr/bin/env python3
"""Human approval evidence changes ledger-authoritative compliance summary."""

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
from lifecycle import human_approved, pre_promotion_lifecycle  # noqa: E402


def verdict_label(summary: dict) -> str:
    return str(summary.get("verdict") or summary.get("compliance_verdict") or "UNKNOWN")


def main() -> None:
    cfg = env_config()
    run_id = str(cfg["run_id"])
    print("Human approval GovAI Core reference.")
    print(f"base_url={cfg['base']} run_id={run_id}")

    blocked_phase = pre_promotion_lifecycle(run_id)
    approval_event = human_approved(run_id)

    print("\nPhase 1 — risky run without human_approved (expect BLOCKED / awaiting approval):")
    for ev in blocked_phase:
        print(f"  - {ev['event_type']}")

    if not execute_guard():
        return

    api_key = require_api_key()
    client = client_from_env()
    timeout = float(cfg["timeout"])

    for ev in blocked_phase:
        print(f"\n-> POST /evidence ({ev['event_type']})")
        print(json.dumps(post_evidence_dict(client, ev, timeout=timeout), indent=2))

    summary_before, _, verify_before = read_run(
        base=str(cfg["base"]),
        api_key=api_key,
        run_id=run_id,
        project=cfg["project"],
        timeout=timeout,
    )
    print_json("compliance-summary BEFORE human_approved", summary_before)
    print(f"verdict_before={verdict_label(summary_before)}")

    print("\nPhase 2 — append human_approved evidence")
    print(json.dumps(post_evidence_dict(client, approval_event, timeout=timeout), indent=2))

    summary_after, export_after, verify_after = read_run(
        base=str(cfg["base"]),
        api_key=api_key,
        run_id=run_id,
        project=cfg["project"],
        timeout=timeout,
    )
    print_json("compliance-summary AFTER human_approved", summary_after)
    print_json("GET /api/export/{run_id} (includes approval)", export_after)
    print_json("GET /verify", verify_after)

    approval_in_export = False
    rows = export_after.get("evidence_events") or []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("event_type") == "human_approved":
                approval_in_export = True
    decision = export_after.get("decision") or {}
    if isinstance(decision, dict) and decision.get("human_approval") is not None:
        approval_in_export = True

    print(f"verdict_after={verdict_label(summary_after)}")
    print(f"human_approval_in_export={approval_in_export}")

    if verify_after.get("ok") is not True:
        raise RuntimeError(f"verify failed: {verify_after}")

    print(
        "\nNote: verdict may remain BLOCKED until model_promoted and remaining lifecycle "
        "requirements are satisfied; human_approved still updates approval projection."
    )


if __name__ == "__main__":
    main()
