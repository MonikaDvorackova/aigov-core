"""Governance lifecycle event fixtures (ledger POST /evidence)."""

from __future__ import annotations

from typing import Any


def _base(run_id: str, event_id: str, event_type: str, ts: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "ts_utc": ts,
        "actor": "reference-integration",
        "system": "govai-core-examples",
        "run_id": run_id,
        "payload": payload,
    }


def discovery(run_id: str) -> dict[str, Any]:
    return _base(
        run_id,
        f"{run_id}-disc",
        "ai_discovery_reported",
        "2026-01-01T00:00:01Z",
        {"openai": True, "transformers": False, "model_artifacts": True},
    )


def data_registered(run_id: str) -> dict[str, Any]:
    return _base(
        run_id,
        f"{run_id}-data",
        "data_registered",
        "2026-01-01T00:00:02Z",
        {
            "ai_system_id": "as-ref",
            "dataset_id": "ds-ref",
            "dataset": "ds",
            "dataset_version": "v1",
            "dataset_fingerprint": "fp-ref",
            "dataset_governance_id": "dg-ref",
            "dataset_governance_commitment": "basic",
            "source": "internal",
            "intended_use": "reference",
            "limitations": "demo",
            "quality_summary": "ok",
            "governance_status": "registered",
        },
    )


def model_trained(run_id: str) -> dict[str, Any]:
    return _base(
        run_id,
        f"{run_id}-train",
        "model_trained",
        "2026-01-01T00:00:02Z",
        {
            "model_version_id": "mv-ref",
            "ai_system_id": "as-ref",
            "dataset_id": "ds-ref",
            "model_type": "mock-llm",
            "artifact_path": "registry://govai-core/examples/mock-model",
            "artifact_sha256": "abc1234567890123456789012345678901234567890123456789012345678901234",
        },
    )


def evaluation_reported(run_id: str, *, passed: bool = True) -> dict[str, Any]:
    return _base(
        run_id,
        f"{run_id}-eval",
        "evaluation_reported",
        "2026-01-01T00:00:03Z",
        {
            "ai_system_id": "as-ref",
            "dataset_id": "ds-ref",
            "model_version_id": "mv-ref",
            "metric": "accuracy",
            "value": 0.95,
            "threshold": 0.8,
            "passed": passed,
        },
    )


def risk_recorded(run_id: str) -> dict[str, Any]:
    return _base(
        run_id,
        f"{run_id}-risk",
        "risk_recorded",
        "2026-01-01T00:00:04Z",
        {
            "assessment_id": "assess-ref",
            "ai_system_id": "as-ref",
            "dataset_id": "ds-ref",
            "model_version_id": "mv-ref",
            "risk_id": "risk-ref",
            "risk_class": "high",
            "severity": 4.0,
            "likelihood": 0.3,
            "status": "submitted",
            "mitigation": "human review required",
            "owner": "risk_officer",
            "dataset_governance_commitment": "basic",
        },
    )


def risk_reviewed(run_id: str) -> dict[str, Any]:
    return _base(
        run_id,
        f"{run_id}-review",
        "risk_reviewed",
        "2026-01-01T00:00:05Z",
        {
            "assessment_id": "assess-ref",
            "ai_system_id": "as-ref",
            "dataset_id": "ds-ref",
            "model_version_id": "mv-ref",
            "risk_id": "risk-ref",
            "decision": "approve",
            "reviewer": "risk_officer",
            "justification": "acceptable for reference demo",
            "dataset_governance_commitment": "basic",
        },
    )


def human_approved(run_id: str) -> dict[str, Any]:
    return _base(
        run_id,
        f"{run_id}-human",
        "human_approved",
        "2026-01-01T00:00:06Z",
        {
            "scope": "model_promoted",
            "decision": "approve",
            "approver": "compliance_officer",
            "justification": "reference approval",
            "assessment_id": "assess-ref",
            "risk_id": "risk-ref",
            "dataset_governance_commitment": "basic",
            "ai_system_id": "as-ref",
            "dataset_id": "ds-ref",
            "model_version_id": "mv-ref",
        },
    )


def model_promoted(run_id: str) -> dict[str, Any]:
    return _base(
        run_id,
        f"{run_id}-promote",
        "model_promoted",
        "2026-01-01T00:00:07Z",
        {
            "ai_system_id": "as-ref",
            "dataset_id": "ds-ref",
            "model_version_id": "mv-ref",
            "artifact_path": "registry://govai-core/examples/mock-model",
            "artifact_sha256": "abc1234567890123456789012345678901234567890123456789012345678901234",
            "promotion_reason": "reference integration",
            "approved_human_event_id": f"{run_id}-human",
            "assessment_id": "assess-ref",
            "risk_id": "risk-ref",
            "dataset_governance_commitment": "basic",
        },
    )


def pre_promotion_lifecycle(run_id: str, *, include_eval: bool = True) -> list[dict[str, Any]]:
    events = [discovery(run_id), data_registered(run_id), model_trained(run_id)]
    if include_eval:
        events.append(evaluation_reported(run_id, passed=True))
    events.extend([risk_recorded(run_id), risk_reviewed(run_id)])
    return events
