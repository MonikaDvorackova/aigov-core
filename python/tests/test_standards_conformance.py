from __future__ import annotations

import json
from pathlib import Path

from aigov_py.standards.common import canonical_json
from aigov_py.standards.validator import validate_conformance

_REPO = Path(__file__).resolve().parents[2]
_EXAMPLES = _REPO / "examples" / "standards"


def _load_example(name: str) -> dict:
    p = _EXAMPLES / name
    return json.loads(p.read_text(encoding="utf-8"))


def test_examples_validate_via_conformance() -> None:
    for fname in (
        "evidence-pack.valid.json",
        "policy-module.valid.json",
        "decision-trace.valid.json",
    ):
        data = _load_example(fname)
        rep = validate_conformance(data)
        assert rep.ok, (fname, rep.failures)
        assert rep.version
        assert rep.artifact_type
        assert "checks" in rep.as_dict()
        j = canonical_json(rep.as_dict())
        assert j == canonical_json(json.loads(j))


def test_json_shape_keys_sorted() -> None:
    data = _load_example("policy-module.valid.json")
    d = validate_conformance(data).as_dict()
    keys = list(d.keys())
    assert keys == sorted(keys)


def test_policy_module_duplicate_requirement_code() -> None:
    base = _load_example("policy-module.valid.json")
    base["requirements"] = [
        {"code": "dup", "required_evidence": ["ev.a"]},
        {"code": "dup", "required_evidence": ["ev.b"]},
    ]
    rep = validate_conformance(base)
    assert not rep.ok
    assert any(f["code"] == "requirement_code_duplicate" for f in rep.failures)


def test_policy_module_wrong_schema_version() -> None:
    base = _load_example("policy-module.valid.json")
    base["schema_version"] = "govai.standards.governance_policy_module.v0"
    rep = validate_conformance(base)
    assert not rep.ok
    assert any(f["code"] == "unknown_schema_version" for f in rep.failures)


def test_decision_trace_verdict_mismatch() -> None:
    base = _load_example("decision-trace.valid.json")
    base["recorded_gate_verdict"] = "BLOCKED"
    rep = validate_conformance(base)
    assert not rep.ok
    assert any(f["code"] == "recorded_verdict_mismatch" for f in rep.failures)


def test_decision_trace_extra_gate_input_key() -> None:
    base = _load_example("decision-trace.valid.json")
    base["gate_inputs"]["unknown_signal"] = True
    rep = validate_conformance(base)
    assert not rep.ok
    assert any(f["code"] == "gate_inputs_unknown_keys" for f in rep.failures)


def test_evidence_pack_digest_manifest_mismatch() -> None:
    base = _load_example("evidence-pack.valid.json")
    base["digest_manifest"]["entries"][0]["content_digest"] = (
        "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )
    rep = validate_conformance(base)
    assert not rep.ok
    assert any(f["code"] == "digest_manifest_mismatch" for f in rep.failures)


def test_artifact_type_mismatch_flag() -> None:
    data = _load_example("evidence-pack.valid.json")
    rep = validate_conformance(data, artifact_type="governance_policy_module")
    assert not rep.ok
    assert any(f["code"] == "artifact_type_mismatch" for f in rep.failures)


def test_policy_module_digest_deterministic() -> None:
    from aigov_py.standards.policy_module import validate_governance_policy_module_document

    data = _load_example("policy-module.valid.json")
    r1 = validate_governance_policy_module_document(data)
    r2 = validate_governance_policy_module_document(data)
    assert r1.ok and r2.ok
    assert r1.digest == r2.digest


def test_decision_trace_digest_deterministic() -> None:
    from aigov_py.standards.decision_trace import validate_governance_decision_trace_document

    data = _load_example("decision-trace.valid.json")
    r1 = validate_governance_decision_trace_document(data)
    r2 = validate_governance_decision_trace_document(data)
    assert r1.ok and r2.ok
    assert r1.digest == r2.digest
