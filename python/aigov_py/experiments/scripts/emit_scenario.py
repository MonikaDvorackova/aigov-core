#!/usr/bin/env python3
"""
Emit GovAI evidence events for real-world CI injection scenarios.

Uses the hosted audit sequence aligned with ``.github/workflows/govai-smoke.yml``:
``ai_discovery_reported`` → ``evaluation_reported`` → ``risk_reviewed`` → ``human_approved`` → ``model_promoted``.

Scenario naming follows the experiment protocol (mapped to server event types):
  - **missing_evidence** — omit ``evaluation_reported`` (policy “registered evaluation evidence”).
  - **missing_approval** — omit ``human_approved`` and ``model_promoted``.
  - **broken_traceability** — POST all events under ``GOVAI_EMIT_RUN_ID``; ``govai check`` must use a
    different ``GOVAI_CHECK_RUN_ID`` (set in the workflow).

Environment (required):
  GOVAI_AUDIT_BASE_URL, GOVAI_API_KEY, GOVAI_PROJECT, SCENARIO
  GOVAI_CHECK_RUN_ID — run_id used later by ``govai check`` (authoritative for the compliance decision).
  GOVAI_EMIT_RUN_ID — optional; defaults to GOVAI_CHECK_RUN_ID. For broken_traceability must differ.

Exit code 0 only if every emitted POST returns HTTP 2xx (skipped steps do not POST).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

import requests

SCENARIOS = frozenset({"missing_evidence", "missing_approval", "broken_traceability"})


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require(name: str) -> str:
    v = (os.environ.get(name) or "").strip()
    if not v:
        print(f"ERROR: missing required environment variable {name}", file=sys.stderr)
        sys.exit(2)
    return v


def _post_evidence(
    *,
    base_url: str,
    api_key: str,
    project: str,
    body: dict[str, Any],
) -> None:
    url = base_url.rstrip("/") + "/evidence"
    r = requests.post(
        url,
        json=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "X-GovAI-Project": project,
            "Content-Type": "application/json",
        },
        timeout=60,
    )
    print(json.dumps({"http_status": r.status_code, "body": r.text[:4000]}, indent=2))
    r.raise_for_status()


def main() -> int:
    p = argparse.ArgumentParser(description="Emit scenario-specific evidence for GovAI audit injection.")
    p.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        default=os.environ.get("SCENARIO"),
        help="Injection scenario (or env SCENARIO).",
    )
    args = p.parse_args()
    scenario = args.scenario
    if not scenario:
        print("ERROR: --scenario or SCENARIO required", file=sys.stderr)
        return 2

    base_url = _require("GOVAI_AUDIT_BASE_URL")
    api_key = _require("GOVAI_API_KEY")
    project = _require("GOVAI_PROJECT")
    check_rid = _require("GOVAI_CHECK_RUN_ID")
    emit_rid = (os.environ.get("GOVAI_EMIT_RUN_ID") or "").strip() or check_rid

    if scenario != "broken_traceability" and emit_rid != check_rid:
        print(
            "WARNING: GOVAI_EMIT_RUN_ID differs from GOVAI_CHECK_RUN_ID but scenario is not broken_traceability",
            file=sys.stderr,
        )

    ts = _utc()
    ai_system_id = "rwci-ai"
    dataset_id = "rwci_dataset_v1"
    dataset_commitment = "basic_compliance"
    model_version_id = f"mv_{emit_rid}"
    assessment_id = f"asmt_{emit_rid}"
    risk_id = f"risk_{emit_rid}"
    artifact_path = f"artifacts/model_{emit_rid}.joblib"

    suffix = f"{emit_rid}_{uuid.uuid4().hex[:8]}"
    human_event_id = f"evt_rwci_human_approved_{suffix}"

    def post(name: str, event_type: str, payload: dict[str, Any], eid: str | None = None) -> None:
        body = {
            "event_id": eid or f"evt_rwci_{event_type}_{suffix}",
            "event_type": event_type,
            "ts_utc": ts,
            "actor": "rwci_injection",
            "system": "github_actions",
            "run_id": emit_rid,
            "payload": payload,
        }
        print(f"\n--- POST {name} ({event_type}) run_id={emit_rid} ---")
        _post_evidence(base_url=base_url, api_key=api_key, project=project, body=body)

    # 1) ai_discovery_reported — always
    post(
        "ai_discovery",
        "ai_discovery_reported",
        {"openai": False, "transformers": False, "model_artifacts": False},
    )

    # 2) evaluation_reported — skip for missing_evidence (policy “registered evaluation” gap)
    if scenario != "missing_evidence":
        post(
            "evaluation",
            "evaluation_reported",
            {
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "metric": "accuracy",
                "value": 0.95,
                "threshold": 0.8,
                "passed": True,
            },
        )
    else:
        print("\n--- SKIP evaluation_reported (missing_evidence) ---")

    # 3) risk_reviewed
    post(
        "risk",
        "risk_reviewed",
        {
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
            "risk_id": risk_id,
            "assessment_id": assessment_id,
            "dataset_governance_commitment": dataset_commitment,
            "decision": "approve",
            "reviewer": "risk_officer",
            "justification": "rwci injection",
        },
    )

    if scenario == "missing_approval":
        print("\nEmit complete for missing_approval (human_approved / model_promoted omitted).")
        return 0

    # 4) human_approved
    post(
        "human",
        "human_approved",
        {
            "scope": "model_promoted",
            "decision": "approve",
            "approver": "compliance_officer",
            "justification": "rwci injection",
            "assessment_id": assessment_id,
            "risk_id": risk_id,
            "dataset_governance_commitment": dataset_commitment,
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
        },
        eid=human_event_id,
    )

    # 5) model_promoted
    post(
        "promotion",
        "model_promoted",
        {
            "artifact_path": artifact_path,
            "promotion_reason": "rwci_injection",
            "assessment_id": assessment_id,
            "risk_id": risk_id,
            "dataset_governance_commitment": dataset_commitment,
            "approved_human_event_id": human_event_id,
            "ai_system_id": ai_system_id,
            "dataset_id": dataset_id,
            "model_version_id": model_version_id,
        },
    )

    print("\nEmit complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
