#!/usr/bin/env python3
"""
End-to-end GovAI audit demo: one run_id, full v0.4_human_approval lifecycle.

Requires the Rust audit service (see README Quickstart). No mocks.

Run from repo root with the local SDK on PYTHONPATH, e.g.:
  source python/.venv/bin/activate
  python examples/demo_govai.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_SYS_PATH_INSERTED = str(REPO_ROOT / "python")
if _SYS_PATH_INSERTED not in sys.path:
    sys.path.insert(0, _SYS_PATH_INSERTED)

from govai import (  # noqa: E402
    GovAIAPIError,
    GovAIClient,
    GovAIHTTPError,
    get_compliance_summary,
    submit_event,
    verify_chain,
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _emit(client: GovAIClient, label: str, body: dict) -> dict:
    print(f"--- Emitting: {label} ---", flush=True)
    try:
        return submit_event(client, body)
    except GovAIAPIError as e:
        print(f"ERROR: event {label} rejected by API: {e}", flush=True)
        if getattr(e, "payload", None):
            print(json.dumps(e.payload, indent=2), flush=True)
        sys.exit(1)
    except GovAIHTTPError as e:
        print(f"ERROR: event {label} HTTP failure: {e}", flush=True)
        if e.body_text:
            print(e.body_text[:2000], flush=True)
        sys.exit(1)


def _compliance_state(summary: dict) -> str:
    """Derive VALID | BLOCKED | INVALID from compliance summary (README decision order)."""
    if summary.get("ok") is not True:
        return "BLOCKED"
    cs = summary.get("current_state")
    if not isinstance(cs, dict):
        return "BLOCKED"
    model = cs.get("model") if isinstance(cs.get("model"), dict) else {}
    approval = cs.get("approval") if isinstance(cs.get("approval"), dict) else {}
    promotion = model.get("promotion") if isinstance(model.get("promotion"), dict) else {}

    ev_passed = model.get("evaluation_passed")
    if ev_passed is False:
        return "INVALID"
    if ev_passed is not True:
        return "BLOCKED"

    decision = approval.get("human_approval_decision")
    if not isinstance(decision, str) or decision.strip().lower() != "approve":
        return "BLOCKED"

    if promotion.get("model_promoted_present") is not True:
        return "BLOCKED"

    return "VALID"


def main() -> None:
    base_url = (os.environ.get("GOVAI_AUDIT_BASE_URL") or "").strip() or "http://127.0.0.1:8088"
    api_key = (os.environ.get("GOVAI_API_KEY") or "").strip() or None
    client = GovAIClient(base_url.rstrip("/"), api_key=api_key)

    run_id = str(uuid.uuid4())
    human_event_id = f"ha_{run_id}"

    # Identifiers aligned with README “Example Use Case” (retail bank, CNP fraud scoring).
    ai_system_id = "cnp-fraud-scoring"
    dataset_id = "txn_fraud_dataset_v1"
    dataset_commitment = "basic_compliance"
    model_version_id = f"model_version_{run_id}"
    assessment_id = f"assessment_{run_id}"
    risk_id = f"risk_{run_id}"

    dataset_fingerprint = (
        "sha256:" + hashlib.sha256(b"govai-demo|txn_fraud_dataset_v1|v1|snapshot").hexdigest()
    )

    # Measured metrics; primary scalar for policy-shaped evaluation is F1 (precision/recall also recorded).
    precision = 0.94
    recall = 0.91
    false_positive_rate = 0.02
    denom = precision + recall
    f1 = (2.0 * precision * recall / denom) if denom else 0.0
    eval_threshold = 0.88
    eval_passed = f1 >= eval_threshold

    actor = "fraud-train-ci"
    system = "fraud-model-training-pipeline"

    _emit(
        client,
        "data_registered",
        {
            "event_id": str(uuid.uuid4()),
            "event_type": "data_registered",
            "ts_utc": now_utc(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "dataset": "card_not_present_transaction_features",
                "dataset_version": "v1",
                "dataset_fingerprint": dataset_fingerprint,
                "dataset_governance_id": "gov_fraud_txn_v1",
                "dataset_governance_commitment": dataset_commitment,
                "source": "internal",
                "intended_use": "Online transaction fraud scoring for card-not-present authorizations.",
                "limitations": "Demo snapshot; not production population coverage.",
                "quality_summary": "Validated sample; fingerprinted for traceability.",
                "governance_status": "registered",
            },
        },
    )

    _emit(
        client,
        "model_trained",
        {
            "event_id": str(uuid.uuid4()),
            "event_type": "model_trained",
            "ts_utc": now_utc(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "model_version": model_version_id,
                "model_type": "sklearn_logistic_regression",
                "artifact_path": f"registry://models/{model_version_id}",
            },
        },
    )

    # evaluation_reported: `metric`, `value`, `threshold`, and `passed` are required by the ingest schema
    # (v0.4_human_approval); embedded policy still enforces promotion gates from the persisted evaluation.
    _emit(
        client,
        "evaluation_reported",
        {
            "event_id": str(uuid.uuid4()),
            "event_type": "evaluation_reported",
            "ts_utc": now_utc(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "metric": "f1",
                "value": f1,
                "threshold": eval_threshold,
                "passed": eval_passed,
                "precision": precision,
                "recall": recall,
                "false_positive_rate": false_positive_rate,
            },
        },
    )

    _emit(
        client,
        "risk_recorded",
        {
            "event_id": str(uuid.uuid4()),
            "event_type": "risk_recorded",
            "ts_utc": now_utc(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "assessment_id": assessment_id,
                "risk_id": risk_id,
                "dataset_governance_commitment": dataset_commitment,
                "risk_class": "operational",
                "severity": 3.0,
                "likelihood": 0.25,
                "status": "submitted",
                "mitigation": "Monitoring and thresholded rollout; human approval required before promotion.",
                "owner": "model_risk_team",
            },
        },
    )

    _emit(
        client,
        "risk_mitigated",
        {
            "event_id": str(uuid.uuid4()),
            "event_type": "risk_mitigated",
            "ts_utc": now_utc(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "assessment_id": assessment_id,
                "risk_id": risk_id,
                "dataset_governance_commitment": dataset_commitment,
                "status": "mitigated",
                "mitigation": "Controls applied: rate limits, shadow mode evaluation, rollback plan documented.",
            },
        },
    )

    _emit(
        client,
        "risk_reviewed",
        {
            "event_id": str(uuid.uuid4()),
            "event_type": "risk_reviewed",
            "ts_utc": now_utc(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
                "assessment_id": assessment_id,
                "risk_id": risk_id,
                "dataset_governance_commitment": dataset_commitment,
                "decision": "approve",
                "reviewer": "second_line_risk",
                "justification": "Residual risk acceptable for governed demo scope; evaluation gate passed.",
            },
        },
    )

    _emit(
        client,
        "human_approved",
        {
            "event_id": human_event_id,
            "event_type": "human_approved",
            "ts_utc": now_utc(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "scope": "model_promoted",
                "decision": "approve",
                "approver": "compliance_officer",
                "justification": "Assessment and dataset commitment verified; promotion authorized for this run.",
                "assessment_id": assessment_id,
                "risk_id": risk_id,
                "dataset_governance_commitment": dataset_commitment,
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
            },
        },
    )

    artifact_path = f"registry://artifacts/model/{model_version_id}"

    _emit(
        client,
        "model_promoted",
        {
            "event_id": str(uuid.uuid4()),
            "event_type": "model_promoted",
            "ts_utc": now_utc(),
            "actor": actor,
            "system": system,
            "run_id": run_id,
            "payload": {
                "artifact_path": artifact_path,
                "promotion_reason": "human_approved_and_policy_gates_satisfied",
                "assessment_id": assessment_id,
                "risk_id": risk_id,
                "dataset_governance_commitment": dataset_commitment,
                "approved_human_event_id": human_event_id,
                "ai_system_id": ai_system_id,
                "dataset_id": dataset_id,
                "model_version_id": model_version_id,
            },
        },
    )

    try:
        summary = get_compliance_summary(client, run_id)
    except GovAIHTTPError as e:
        print(f"ERROR: get_compliance_summary failed: {e}", flush=True)
        sys.exit(1)

    state = _compliance_state(summary)
    print("", flush=True)
    print("=== COMPLIANCE DECISION ===", flush=True)
    print(f"STATE: {state}", flush=True)
    print(f"run_id={run_id}", flush=True)

    # verify_chain() wraps GET /verify: checks hash-chain integrity of the whole append-only ledger,
    # not an isolated slice for this run_id (the SDK has no run-scoped chain API).
    try:
        chain = verify_chain(client)
    except GovAIHTTPError as e:
        print(f"ERROR: verify_chain failed: {e}", flush=True)
        sys.exit(1)

    chain_ok = chain.get("ok") is True
    print("", flush=True)
    print("=== AUDIT VERIFICATION ===", flush=True)
    print(f"run_id (this demo)={run_id}", flush=True)
    print("ledger_scope: full append-only audit log hash chain (GET /verify)", flush=True)
    print(f"CHAIN_VALID: {str(chain_ok).lower()}", flush=True)
    if not chain_ok:
        print(json.dumps(chain, indent=2), flush=True)
        sys.exit(1)

    if state != "VALID":
        print("", flush=True)
        print("NOTE: compliance state is not VALID; inspect summary:", flush=True)
        print(json.dumps(summary, indent=2), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
