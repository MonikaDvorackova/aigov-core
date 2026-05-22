from __future__ import annotations

import re
from pathlib import Path

import pytest

from aigov_py.agent_action_signatures import (
    SIGNATURE_ALGORITHMS,
    AgentActionDigest,
    AgentActionSignaturePlan,
    AgentActionSigningEnvelope,
    AgentSigningKeyRef,
    SignatureVerificationExpectation,
    build_agent_action_signature_plan,
    build_agent_action_signing_envelope,
    build_signature_verification_expectation,
    compute_envelope_digest,
    normalize_payload_digest,
)

_VALID_HEX = "a" * 64


def _base_kwargs() -> dict:
    return {
        "tenant_id": "t1",
        "agent_id": "agent1",
        "principal_id": "p1",
        "action_id": "act1",
        "capability_id": "govai.test.cap",
        "policy_snapshot_id": "pol-snap-1",
        "payload_digest": _VALID_HEX,
        "signing_key_ref": "kms:key/abc",
        "signature_algorithm": "ED25519",
    }


def test_valid_envelope_and_plan_build() -> None:
    env = build_agent_action_signing_envelope(**_base_kwargs())
    assert isinstance(env, AgentActionSigningEnvelope)
    assert env.envelope_digest == compute_envelope_digest(
        {
            "action_id": "act1",
            "agent_id": "agent1",
            "capability_id": "govai.test.cap",
            "delegation_id": "",
            "payload_digest": normalize_payload_digest(_VALID_HEX),
            "policy_snapshot_id": "pol-snap-1",
            "principal_id": "p1",
            "signature_algorithm": "ED25519",
            "signing_key_ref": "kms:key/abc",
            "tenant_id": "t1",
            "trace_id": "",
        }
    )

    plan = build_agent_action_signature_plan(
        **_base_kwargs(),
        delegation_id=" del-1 ",
        trace_id=" trace-9 ",
        expected_signature_ref="sig-ref-placeholder",
    )
    assert isinstance(plan, AgentActionSignaturePlan)
    assert plan.envelope.delegation_id == "del-1"
    assert plan.envelope.trace_id == "trace-9"
    assert plan.verification.expected_signature_ref == "sig-ref-placeholder"


@pytest.mark.parametrize(
    "field",
    [
        "tenant_id",
        "agent_id",
        "principal_id",
        "action_id",
        "capability_id",
        "policy_snapshot_id",
    ],
)
def test_missing_required_string_field_fails(field: str) -> None:
    kw = _base_kwargs()
    kw[field] = "   "
    with pytest.raises(ValueError, match="required"):
        build_agent_action_signing_envelope(**kw)


def test_invalid_payload_digest_fails() -> None:
    kw = _base_kwargs()
    kw["payload_digest"] = "not-a-digest"
    with pytest.raises(ValueError, match="payload_digest"):
        build_agent_action_signing_envelope(**kw)


@pytest.mark.parametrize("alg", sorted(SIGNATURE_ALGORITHMS))
def test_supported_algorithms(alg: str) -> None:
    kw = _base_kwargs()
    kw["signature_algorithm"] = alg
    env = build_agent_action_signing_envelope(**kw)
    assert env.signature_algorithm == alg


def test_unsupported_signature_algorithm_fails() -> None:
    kw = _base_kwargs()
    kw["signature_algorithm"] = "RSA_PSS_SHA256"
    with pytest.raises(ValueError, match="unsupported signature_algorithm"):
        build_agent_action_signing_envelope(**kw)


def test_deterministic_envelope_digest_stable() -> None:
    kw = _base_kwargs()
    e1 = build_agent_action_signing_envelope(**kw)
    e2 = build_agent_action_signing_envelope(**kw)
    assert e1.envelope_digest == e2.envelope_digest


def test_changed_payload_digest_changes_envelope_digest() -> None:
    kw = _base_kwargs()
    env_a = build_agent_action_signing_envelope(**kw)
    kw["payload_digest"] = "b" * 64
    env_b = build_agent_action_signing_envelope(**kw)
    assert env_a.envelope_digest != env_b.envelope_digest


def test_no_raw_payload_fields_on_models() -> None:
    forbidden = {"payload", "raw_payload", "action_payload", "body", "content"}
    for cls in (
        AgentActionSigningEnvelope,
        AgentActionSignaturePlan,
        AgentSigningKeyRef,
        AgentActionDigest,
        SignatureVerificationExpectation,
    ):
        names = getattr(cls, "__annotations__", {}).keys()
        for n in names:
            assert n not in forbidden
            assert not n.endswith("_payload") or n == "payload_digest"


def test_optional_refs_passed_through_stripped() -> None:
    env = build_agent_action_signing_envelope(
        **_base_kwargs(),
        delegation_id="  d1  ",
        trace_id="  tr2  ",
    )
    assert env.delegation_id == "d1"
    assert env.trace_id == "tr2"


def test_empty_optional_ref_fails() -> None:
    with pytest.raises(ValueError, match="delegation_id"):
        build_agent_action_signing_envelope(**_base_kwargs(), delegation_id=" ")
    with pytest.raises(ValueError, match="trace_id"):
        build_agent_action_signing_envelope(**_base_kwargs(), trace_id=" ")


def test_expected_signature_ref_empty_fails() -> None:
    env = build_agent_action_signing_envelope(**_base_kwargs())
    with pytest.raises(ValueError, match="expected_signature_ref"):
        build_signature_verification_expectation(env, expected_signature_ref="  ")


def test_no_other_aigov_py_modules_import_helper() -> None:
    root = Path(__file__).resolve().parents[1] / "aigov_py"
    import_re = re.compile(
        r"^\s*(?:from\s+aigov_py\.agent_action_signatures\s+import"
        r"|import\s+aigov_py\.agent_action_signatures)\s*",
    )
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if path.name == "agent_action_signatures.py":
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if import_re.match(line):
                offenders.append(f"{path}:{i}:{line.strip()}")
    assert offenders == [], offenders


def test_sha256_prefix_payload_accepted() -> None:
    hx = "ab" * 32
    assert normalize_payload_digest(f"sha256:{hx}") == f"sha256:{hx.lower()}"
