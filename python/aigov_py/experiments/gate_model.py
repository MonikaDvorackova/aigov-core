from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Verdict = Literal["VALID", "INVALID", "BLOCKED"]
ModelValidation = Literal["passed", "failed"]
EvaluationResult = Literal["pass", "fail"]


@dataclass(frozen=True)
class GateAblation:
    """When True, the corresponding enforcement clause is skipped (treated as satisfied)."""

    skip_events_digest: bool = False
    skip_export_digest: bool = False
    skip_artifact_bound: bool = False
    skip_policy_version: bool = False
    skip_approval: bool = False
    skip_trace: bool = False


def _rubric_path() -> Path:
    return Path(__file__).resolve().with_name("scenario_rubric.json")


def load_scenario_rubric() -> dict[str, Any]:
    raw = json.loads(_rubric_path().read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("rubric root must be an object")
    scenarios = raw.get("scenarios")
    if not isinstance(scenarios, list):
        raise TypeError("rubric.scenarios must be a list")
    return raw


def rubric_scenarios() -> list[dict[str, Any]]:
    return list(load_scenario_rubric()["scenarios"])  # type: ignore[arg-type]


def rubric_index_by_name() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rubric_scenarios():
        name = row.get("scenario_name")
        if not isinstance(name, str):
            raise TypeError("scenario_name must be a string")
        if name in out:
            raise ValueError(f"duplicate scenario_name in rubric: {name}")
        out[name] = row
    return out


_RUBRIC_INDEX: dict[str, dict[str, Any]] | None = None


def get_rubric_row(scenario_name: str) -> dict[str, Any]:
    global _RUBRIC_INDEX
    if _RUBRIC_INDEX is None:
        _RUBRIC_INDEX = rubric_index_by_name()
    if scenario_name not in _RUBRIC_INDEX:
        raise KeyError(f"unknown scenario in rubric: {scenario_name}")
    return _RUBRIC_INDEX[scenario_name]


def expected_verdict_from_rubric(scenario_name: str) -> Verdict:
    row = get_rubric_row(scenario_name)
    ev = row.get("expected_verdict")
    if ev not in ("VALID", "INVALID", "BLOCKED"):
        raise TypeError(f"bad expected_verdict for {scenario_name}: {ev!r}")
    return ev  # type: ignore[return-value]


def scenario_names_in_order() -> tuple[str, ...]:
    return tuple(str(r["scenario_name"]) for r in rubric_scenarios())


# Injected violation scenarios only (for baseline false-negative denominators).
FAILURE_TAXONOMY: tuple[str, ...] = tuple(
    str(r["scenario_name"])
    for r in rubric_scenarios()
    if r.get("injected_violation") is True
)


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    condition: str
    is_injected_failure: bool
    should_pass: bool
    model_validation: ModelValidation
    evidence_complete: bool
    ai_discovery_present: bool
    evaluation_result: EvaluationResult
    evaluation_internal_consistent: bool
    approval: str
    trace_consistent: bool
    run_available: bool
    evidence_pack_present: bool
    events_content_sha256_match: bool
    export_digest_match: bool
    artifact_bound_verification: bool
    policy_version_match: bool
    approval_is_stale: bool
    causal_evaluation_before_approval: bool
    run_id_matches_decision_scope: bool
    baseline_verdict: Verdict
    pipeline_baseline_verdict: Verdict
    gate_verdict: Verdict
    expected_gate_verdict: Verdict
    gate_matches_rubric: bool


def baseline_model_only(model_validation: ModelValidation) -> Verdict:
    if model_validation == "passed":
        return "VALID"
    return "INVALID"


def pipeline_completeness_baseline(
    *,
    model_validation: ModelValidation,
    evaluation_result: EvaluationResult,
    run_available: bool,
    evidence_complete: bool,
    approval: str,
) -> Verdict:
    """Baseline 2: pipeline completeness without digest, pack, artifact binding, or policy checks."""
    if model_validation != "passed":
        return "INVALID"
    if evaluation_result != "pass":
        return "INVALID"
    if run_available is not True:
        return "INVALID"
    if evidence_complete is not True:
        return "INVALID"
    if approval != "granted":
        return "INVALID"
    return "VALID"


def decision_gate_verdict(
    *,
    evaluation_result: EvaluationResult,
    evaluation_internal_consistent: bool,
    run_available: bool,
    evidence_pack_present: bool,
    events_content_sha256_match: bool,
    export_digest_match: bool,
    artifact_bound_verification: bool,
    policy_version_match: bool,
    evidence_complete: bool,
    ai_discovery_present: bool,
    approval: str,
    approval_is_stale: bool,
    causal_evaluation_before_approval: bool,
    run_id_matches_decision_scope: bool,
    trace_consistent: bool,
    ablation: GateAblation | None = None,
) -> Verdict:
    ab = ablation or GateAblation()

    if evaluation_result == "fail":
        return "INVALID"
    if evaluation_internal_consistent is not True:
        return "BLOCKED"
    if run_available is False:
        return "BLOCKED"
    if evidence_pack_present is not True:
        return "BLOCKED"
    if not ab.skip_events_digest and events_content_sha256_match is not True:
        return "BLOCKED"
    if not ab.skip_export_digest and export_digest_match is not True:
        return "BLOCKED"
    if not ab.skip_artifact_bound and artifact_bound_verification is not True:
        return "BLOCKED"
    if not ab.skip_policy_version and policy_version_match is not True:
        return "BLOCKED"
    if evidence_complete is not True:
        return "BLOCKED"
    if ai_discovery_present is not True:
        return "BLOCKED"
    if not ab.skip_approval:
        if approval != "granted":
            return "BLOCKED"
        if approval_is_stale is True:
            return "BLOCKED"
        if causal_evaluation_before_approval is not True:
            return "BLOCKED"
    if not ab.skip_trace:
        if run_id_matches_decision_scope is not True:
            return "BLOCKED"
        if trace_consistent is not True:
            return "BLOCKED"
    return "VALID"


def decision_gate_verdict_from_fields(
    fields: dict[str, Any], *, ablation: GateAblation | None = None
) -> Verdict:
    er = fields["evaluation_result"]
    if er not in ("pass", "fail"):
        raise TypeError("evaluation_result")
    return decision_gate_verdict(
        evaluation_result=er,  # type: ignore[arg-type]
        evaluation_internal_consistent=bool(fields["evaluation_internal_consistent"]),
        run_available=bool(fields["run_available"]),
        evidence_pack_present=bool(fields["evidence_pack_present"]),
        events_content_sha256_match=bool(fields["events_content_sha256_match"]),
        export_digest_match=bool(fields["export_digest_match"]),
        artifact_bound_verification=bool(fields["artifact_bound_verification"]),
        policy_version_match=bool(fields["policy_version_match"]),
        evidence_complete=bool(fields["evidence_complete"]),
        ai_discovery_present=bool(fields["ai_discovery_present"]),
        approval=str(fields["approval"]),
        approval_is_stale=bool(fields["approval_is_stale"]),
        causal_evaluation_before_approval=bool(fields["causal_evaluation_before_approval"]),
        run_id_matches_decision_scope=bool(fields["run_id_matches_decision_scope"]),
        trace_consistent=bool(fields["trace_consistent"]),
        ablation=ablation,
    )


def make_base_fields() -> dict[str, object]:
    """Backward-compatible base field bundle (re-export shape for artifact_bound_enforcement)."""
    from aigov_py.experiments.scenario_fields import make_base_fields as _mb

    return _mb()


def apply_failure_type(fields: dict[str, object], failure_type: str) -> dict[str, object]:
    """
    Legacy helper: map old seven-class names to the extended field bundle.
    Prefer scenario_fields.fields_for_scenario for new code.
    """
    from aigov_py.experiments import scenario_fields as sf

    legacy_map = {
        "missing_audit_evidence": "missing_audit_evidence",
        "missing_ai_discovery_output": "missing_ai_discovery_output",
        "missing_approval_record": "missing_approval_record",
        "failed_compliance_evaluation": "failed_compliance_evaluation",
        "inconsistent_run_context": "inconsistent_run_context",
        "unavailable_audit_run": "unavailable_audit_run",
        "partial_evidence": "partial_evidence_bundle",
    }
    if failure_type not in legacy_map:
        raise ValueError(f"Unsupported failure type: {failure_type}")
    return sf.fields_for_scenario(legacy_map[failure_type])


def run_id_for_cfi(index_1_based: int) -> str:
    return f"cfi-{index_1_based:04d}"


def build_run(
    *,
    run_id: str,
    condition: str,
    is_injected_failure: bool,
    should_pass: bool,
    fields: dict[str, object],
    ablation: GateAblation | None = None,
) -> RunRecord:
    mv = fields["model_validation"]
    if mv not in ("passed", "failed"):
        raise TypeError("model_validation")

    expected = expected_verdict_from_rubric(condition)
    gate_verdict = decision_gate_verdict_from_fields(fields, ablation=ablation)

    pipe = pipeline_completeness_baseline(
        model_validation=mv,  # type: ignore[arg-type]
        evaluation_result=fields["evaluation_result"],  # type: ignore[arg-type]
        run_available=bool(fields["run_available"]),
        evidence_complete=bool(fields["evidence_complete"]),
        approval=str(fields["approval"]),
    )

    return RunRecord(
        run_id=run_id,
        condition=condition,
        is_injected_failure=is_injected_failure,
        should_pass=should_pass,
        model_validation=mv,  # type: ignore[arg-type]
        evidence_complete=bool(fields["evidence_complete"]),
        ai_discovery_present=bool(fields["ai_discovery_present"]),
        evaluation_result=fields["evaluation_result"],  # type: ignore[arg-type]
        evaluation_internal_consistent=bool(fields["evaluation_internal_consistent"]),
        approval=str(fields["approval"]),
        trace_consistent=bool(fields["trace_consistent"]),
        run_available=bool(fields["run_available"]),
        evidence_pack_present=bool(fields["evidence_pack_present"]),
        events_content_sha256_match=bool(fields["events_content_sha256_match"]),
        export_digest_match=bool(fields["export_digest_match"]),
        artifact_bound_verification=bool(fields["artifact_bound_verification"]),
        policy_version_match=bool(fields["policy_version_match"]),
        approval_is_stale=bool(fields["approval_is_stale"]),
        causal_evaluation_before_approval=bool(fields["causal_evaluation_before_approval"]),
        run_id_matches_decision_scope=bool(fields["run_id_matches_decision_scope"]),
        baseline_verdict=baseline_model_only(mv),  # type: ignore[arg-type]
        pipeline_baseline_verdict=pipe,
        gate_verdict=gate_verdict,
        expected_gate_verdict=expected,
        gate_matches_rubric=(gate_verdict == expected),
    )
