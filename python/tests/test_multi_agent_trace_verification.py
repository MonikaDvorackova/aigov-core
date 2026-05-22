from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pytest

from aigov_py.multi_agent_trace_verification import (
    TraceSignatureExpectation,
    TraceVerificationRequirement,
    TraceVerificationStatus,
    plan_trace_verification,
)


def _base_requirements(
    *,
    signatures_required: bool = True,
    strict_signatures: bool = False,
    event_chain_required: bool = True,
    event_count_expected: int = 2,
) -> TraceVerificationRequirement:
    return TraceVerificationRequirement(
        signatures_required=signatures_required,
        strict_signatures=strict_signatures,
        event_chain_required=event_chain_required,
        event_count_expected=event_count_expected,
    )


def _base_plan_kwargs():
    sigs = [
        TraceSignatureExpectation(
            action_id="a1",
            signing_key_ref="keys/agent-a",
            signature_algorithm="ed25519",
            expected_signature_ref="sig/a1",
        ),
        TraceSignatureExpectation(
            action_id="a2",
            signing_key_ref="keys/agent-b",
            signature_algorithm="ed25519",
            expected_signature_ref="sig/a2",
        ),
    ]
    return dict(
        tenant_id="t1",
        trace_id="trace-001",
        trace_digest="sha256:" + ("a" * 64),
        policy_snapshot_id="polsnap_123",
        event_count_expected=2,
        requirements=_base_requirements(),
        signature_expectations=sigs,
        event_digest_chain_refs=["evt:1", "evt:2"],
    )


def test_valid_verification_plan_passes():
    plan = plan_trace_verification(**_base_plan_kwargs())
    assert plan.status == TraceVerificationStatus.PASS
    assert plan.plan_digest
    assert all(f.code for f in plan.findings)


def test_missing_tenant_id_fails():
    kw = _base_plan_kwargs()
    kw["tenant_id"] = "   "
    plan = plan_trace_verification(**kw)
    assert plan.status == TraceVerificationStatus.FAIL
    assert any(f.code == "TENANT_ID_REQUIRED" and f.status == TraceVerificationStatus.FAIL for f in plan.findings)


@pytest.mark.parametrize(
    "bad_digest",
    [
        "",
        "nope",
        "sha256:" + ("a" * 63),
        "sha256:" + ("g" * 64),
        ("a" * 63),
        ("z" * 64),
    ],
)
def test_invalid_trace_digest_fails(bad_digest: str):
    kw = _base_plan_kwargs()
    kw["trace_digest"] = bad_digest
    plan = plan_trace_verification(**kw)
    assert plan.status == TraceVerificationStatus.FAIL
    assert any(f.code in {"TRACE_DIGEST_REQUIRED", "TRACE_DIGEST_INVALID"} for f in plan.findings)


def test_signatures_required_without_expected_signature_ref_warns():
    kw = _base_plan_kwargs()
    kw["requirements"] = _base_requirements(signatures_required=True, strict_signatures=False, event_chain_required=True)
    kw["signature_expectations"] = [
        TraceSignatureExpectation(action_id="a1", signing_key_ref="keys/agent-a", signature_algorithm="ed25519"),
    ]
    plan = plan_trace_verification(**kw)
    assert plan.status == TraceVerificationStatus.WARN
    assert any(
        f.code == "EXPECTED_SIGNATURE_REF_MISSING" and f.status == TraceVerificationStatus.WARN for f in plan.findings
    )


def test_strict_signatures_without_expected_signature_ref_fails():
    kw = _base_plan_kwargs()
    kw["requirements"] = _base_requirements(signatures_required=True, strict_signatures=True, event_chain_required=True)
    kw["signature_expectations"] = [
        TraceSignatureExpectation(action_id="a1", signing_key_ref="keys/agent-a", signature_algorithm="ed25519"),
    ]
    plan = plan_trace_verification(**kw)
    assert plan.status == TraceVerificationStatus.FAIL
    assert any(
        f.code == "EXPECTED_SIGNATURE_REF_MISSING" and f.status == TraceVerificationStatus.FAIL for f in plan.findings
    )


def test_event_chain_required_without_chain_refs_fails():
    kw = _base_plan_kwargs()
    kw["event_digest_chain_refs"] = None
    kw["requirements"] = _base_requirements(event_chain_required=True)
    plan = plan_trace_verification(**kw)
    assert plan.status == TraceVerificationStatus.FAIL
    assert any(f.code == "EVENT_CHAIN_REQUIRED_MISSING" for f in plan.findings)


def test_event_chain_not_required_gives_not_applicable_finding():
    kw = _base_plan_kwargs()
    kw["requirements"] = _base_requirements(event_chain_required=False)
    kw["event_digest_chain_refs"] = None
    plan = plan_trace_verification(**kw)
    assert any(
        f.code == "EVENT_CHAIN_NOT_REQUIRED" and f.status == TraceVerificationStatus.NOT_APPLICABLE for f in plan.findings
    )


def test_deterministic_plan_digest_stable():
    plan1 = plan_trace_verification(**_base_plan_kwargs())
    plan2 = plan_trace_verification(**_base_plan_kwargs())
    assert plan1.plan_digest == plan2.plan_digest
    assert [f.code for f in plan1.findings] == [f.code for f in plan2.findings]


def test_changed_finding_input_changes_plan_digest():
    kw1 = _base_plan_kwargs()
    kw2 = _base_plan_kwargs()
    kw2["signature_expectations"] = [
        TraceSignatureExpectation(
            action_id="a1",
            signing_key_ref="keys/agent-a",
            signature_algorithm="ed25519",
            expected_signature_ref="sig/a1",
        )
    ]
    plan1 = plan_trace_verification(**kw1)
    plan2 = plan_trace_verification(**kw2)
    assert plan1.plan_digest != plan2.plan_digest


def test_findings_sorted_deterministically():
    kw = _base_plan_kwargs()
    kw["requirements"] = _base_requirements(signatures_required=True, strict_signatures=False, event_chain_required=True)
    kw["signature_expectations"] = [
        TraceSignatureExpectation(action_id="b", signing_key_ref="", signature_algorithm=None),
        TraceSignatureExpectation(action_id="a", signing_key_ref="", signature_algorithm=None),
    ]
    plan = plan_trace_verification(**kw)
    codes = [f.code for f in plan.findings]
    assert codes == sorted(codes)


def test_no_raw_payload_fields_modeled():
    kw = _base_plan_kwargs()
    plan = plan_trace_verification(**kw)
    d = asdict(plan)
    blob = str(d).lower()
    assert "payload" not in blob
    assert "raw" not in blob


def test_no_runtime_modules_import_helper():
    # We keep the helper planning-only and avoid wiring it into runtime flows.
    repo_root = Path(__file__).resolve().parents[2]
    runtime_files = [
        repo_root / "python" / "aigov_py" / "runtime_governance.py",
        repo_root / "python" / "aigov_py" / "verify.py",
        repo_root / "python" / "aigov_py" / "evaluate.py",
    ]
    for p in runtime_files:
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8")
        assert "multi_agent_trace_verification" not in txt

