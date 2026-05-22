"""
Deterministic synthetic observables per scenario name.

This module intentionally does not import the gate verdict function: scenario
constructors only populate the closed-schema field bundle consumed by the gate.
"""

from __future__ import annotations

from typing import Any


def make_base_fields() -> dict[str, Any]:
    return {
        "model_validation": "passed",
        "evidence_complete": True,
        "ai_discovery_present": True,
        "evaluation_result": "pass",
        "evaluation_internal_consistent": True,
        "approval": "granted",
        "trace_consistent": True,
        "run_available": True,
        "evidence_pack_present": True,
        "events_content_sha256_match": True,
        "export_digest_match": True,
        "artifact_bound_verification": True,
        "policy_version_match": True,
        "approval_is_stale": False,
        "causal_evaluation_before_approval": True,
        "run_id_matches_decision_scope": True,
    }


def fields_for_scenario(scenario_name: str) -> dict[str, Any]:
    """Return synthetic observables for one scenario (decoupled from gate output)."""
    b = make_base_fields()

    if scenario_name == "valid_complete_trace":
        return dict(b)

    if scenario_name == "noisy_but_valid_metadata":
        out = dict(b)
        out["model_validation"] = "failed"
        return out

    if scenario_name == "unknown_optional_metadata":
        return dict(b)

    if scenario_name == "reordered_required_events":
        return dict(b)

    if scenario_name == "duplicated_evidence_event_idempotent":
        return dict(b)

    if scenario_name == "missing_audit_evidence":
        out = dict(b)
        out["evidence_complete"] = False
        return out

    if scenario_name == "missing_ai_discovery_output":
        out = dict(b)
        out["ai_discovery_present"] = False
        return out

    if scenario_name == "missing_evidence_pack":
        out = dict(b)
        out["evidence_pack_present"] = False
        return out

    if scenario_name == "partial_evidence_bundle":
        out = dict(b)
        out["evidence_complete"] = False
        out["events_content_sha256_match"] = False
        out["export_digest_match"] = False
        out["artifact_bound_verification"] = False
        return out

    if scenario_name == "failed_compliance_evaluation":
        out = dict(b)
        out["evaluation_result"] = "fail"
        return out

    if scenario_name == "inconsistent_evaluation_result":
        out = dict(b)
        out["evaluation_result"] = "pass"
        out["evaluation_internal_consistent"] = False
        return out

    if scenario_name == "missing_approval_record":
        out = dict(b)
        out["approval"] = "missing"
        return out

    if scenario_name == "stale_approval":
        out = dict(b)
        out["approval_is_stale"] = True
        return out

    if scenario_name == "approval_recorded_before_evaluation":
        out = dict(b)
        out["causal_evaluation_before_approval"] = False
        return out

    if scenario_name == "invalid_approval_state":
        out = dict(b)
        out["approval"] = "denied"
        return out

    if scenario_name == "inconsistent_run_context":
        out = dict(b)
        out["trace_consistent"] = False
        return out

    if scenario_name == "wrong_run_id":
        out = dict(b)
        out["run_id_matches_decision_scope"] = False
        return out

    if scenario_name == "unavailable_audit_run":
        out = dict(b)
        out["run_available"] = False
        return out

    if scenario_name == "digest_mismatch_events_only":
        out = dict(b)
        out["events_content_sha256_match"] = False
        return out

    if scenario_name == "digest_mismatch_export_only":
        out = dict(b)
        out["export_digest_match"] = False
        return out

    if scenario_name == "policy_version_mismatch":
        out = dict(b)
        out["policy_version_match"] = False
        return out

    if scenario_name == "duplicated_evidence_event_conflicting":
        out = dict(b)
        out["artifact_bound_verification"] = False
        return out

    raise ValueError(f"Unknown scenario_name: {scenario_name}")
