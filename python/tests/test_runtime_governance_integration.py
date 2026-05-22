from __future__ import annotations

import copy
from dataclasses import fields

from aigov_py.runtime_governance import (
    DatasetLineageRef,
    HumanOverrideRef,
    RuntimeControlEvaluation,
    RuntimeControlStatus,
    RuntimeGovernanceContext,
    RuntimeGovernanceSummary,
    RuntimeGovernanceVerdict,
    RuntimeRiskClass,
    summarize_runtime_governance,
    validate_runtime_governance_context,
)


class _NotAControlStatus:
    """Negative test only: wrong type for status."""

    ...


def _hex64(h: str = "a") -> str:
    return h * 64


def _base_ctx(
    **kwargs,
) -> RuntimeGovernanceContext:
    defaults = dict(
        runtime_decision_id="decision-1",
        correlation_id="corr-1",
        tenant_id="tenant-1",
        artifact_digest=_hex64("0"),
        policy_bundle_version="bundle-1.0.0",
        risk_class=RuntimeRiskClass.LIMITED,
        control_evaluations=(
            RuntimeControlEvaluation(
                control_id="ctl-1",
                status=RuntimeControlStatus.PASS,
                reason_codes=(),
                evidence_refs=("ev:1",),
            ),
        ),
        dataset_lineage_refs=(),
        human_override_ref=None,
        ai_act_requirement_refs=(),
    )
    defaults.update(kwargs)
    return RuntimeGovernanceContext(**defaults)


def test_valid_context_with_passing_controls_summarizes_valid() -> None:
    ctx = _base_ctx()
    assert validate_runtime_governance_context(ctx) == ()
    s = summarize_runtime_governance(ctx)
    assert s == RuntimeGovernanceSummary(
        verdict=RuntimeGovernanceVerdict.VALID,
        validation_errors=(),
        failing_control_ids=(),
    )


def test_failing_control_summarizes_invalid() -> None:
    ctx = _base_ctx(
        control_evaluations=(
            RuntimeControlEvaluation(
                control_id="ctl-fail",
                status=RuntimeControlStatus.FAIL,
                reason_codes=("RC_DENIED",),
                evidence_refs=(),
            ),
        ),
    )
    s = summarize_runtime_governance(ctx)
    assert s.verdict == RuntimeGovernanceVerdict.INVALID
    assert s.failing_control_ids == ("ctl-fail",)


def test_missing_required_context_summarizes_blocked() -> None:
    ctx = _base_ctx(correlation_id="   ")
    s = summarize_runtime_governance(ctx)
    assert s.verdict == RuntimeGovernanceVerdict.BLOCKED
    assert s.failing_control_ids == ()
    assert "correlation_id is required" in " ".join(s.validation_errors)


def test_fail_without_reason_code_fails_validation() -> None:
    ctx = _base_ctx(
        control_evaluations=(
            RuntimeControlEvaluation(
                control_id="ctl-1",
                status=RuntimeControlStatus.FAIL,
                reason_codes=(),
                evidence_refs=(),
            ),
        ),
    )
    errs = validate_runtime_governance_context(ctx)
    assert errs
    assert any("FAIL requires at least one" in e for e in errs)
    s = summarize_runtime_governance(ctx)
    assert s.verdict == RuntimeGovernanceVerdict.INVALID
    assert "ctl-1" in s.failing_control_ids


def test_invalid_artifact_digest_fails_validation() -> None:
    ctx = _base_ctx(artifact_digest="not-a-digest")
    errs = validate_runtime_governance_context(ctx)
    assert errs
    s = summarize_runtime_governance(ctx)
    assert s.verdict == RuntimeGovernanceVerdict.BLOCKED


def test_dataset_lineage_digest_invalid_fails_validation() -> None:
    ctx = _base_ctx(
        dataset_lineage_refs=(
            DatasetLineageRef(dataset_id="ds-1", dataset_digest="bad"),
        ),
    )
    errs = validate_runtime_governance_context(ctx)
    assert errs
    s = summarize_runtime_governance(ctx)
    assert s.verdict == RuntimeGovernanceVerdict.BLOCKED


def test_override_target_mismatch_fails_validation() -> None:
    ctx = _base_ctx(
        human_override_ref=HumanOverrideRef(
            override_id="ov-1",
            target_decision_id="other-decision",
        ),
    )
    errs = validate_runtime_governance_context(ctx)
    assert errs
    s = summarize_runtime_governance(ctx)
    assert s.verdict == RuntimeGovernanceVerdict.BLOCKED


def test_not_applicable_control_does_not_block() -> None:
    ctx = _base_ctx(
        control_evaluations=(
            RuntimeControlEvaluation(
                control_id="ctl-na",
                status=RuntimeControlStatus.NOT_APPLICABLE,
                reason_codes=(),
                evidence_refs=(),
            ),
        ),
    )
    s = summarize_runtime_governance(ctx)
    assert s.verdict == RuntimeGovernanceVerdict.VALID


def test_deterministic_repeated_summary() -> None:
    ctx = _base_ctx()
    a = summarize_runtime_governance(ctx)
    b = summarize_runtime_governance(copy.deepcopy(ctx))
    assert a == b
    assert hash(a) == hash(b)


def test_no_raw_user_content_fields_on_context() -> None:
    """Integration model carries ids, digests, refs — no free-text message/prompt fields."""
    banned_substrings = ("user", "prompt", "message", "content", "text_body")
    for f in fields(RuntimeGovernanceContext):
        name_l = f.name.lower()
        for ban in banned_substrings:
            assert ban not in name_l


def test_sha256_prefix_digest_accepted() -> None:
    ctx = _base_ctx(artifact_digest="sha256:" + _hex64("f"))
    assert validate_runtime_governance_context(ctx) == ()


def test_invalid_control_status_fails_validation_summarizes_blocked() -> None:
    bad_eval = RuntimeControlEvaluation(
        control_id="ctl-1",
        status=_NotAControlStatus(),  # type: ignore[arg-type]
        reason_codes=(),
        evidence_refs=(),
    )
    ctx = _base_ctx(control_evaluations=(bad_eval,))
    errs = validate_runtime_governance_context(ctx)
    assert errs
    assert any("status must be a member of RuntimeControlStatus" in e for e in errs)
    s = summarize_runtime_governance(ctx)
    assert s.verdict == RuntimeGovernanceVerdict.BLOCKED
    assert s.failing_control_ids == ()

