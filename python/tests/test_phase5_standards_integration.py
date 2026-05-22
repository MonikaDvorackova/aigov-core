from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aigov_py.standards.capability_policy import validate_capability_policy_document
from aigov_py.standards.delegation_graph import validate_delegation_graph_document
from aigov_py.standards.evidence_pack import validate_governance_evidence_pack_document
from aigov_py.standards.trace_verification import validate_trace_verification_plan_document


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _examples_dir() -> Path:
    return _repo_root() / "examples" / "standards"


@pytest.mark.parametrize(
    "name,validate_fn",
    [
        ("capability_policy.valid.json", validate_capability_policy_document),
        ("delegation_graph.valid.json", validate_delegation_graph_document),
        ("trace_verification_plan.valid.json", validate_trace_verification_plan_document),
        ("governance_evidence_pack.valid.json", validate_governance_evidence_pack_document),
    ],
)
def test_all_example_json_files_validate(name: str, validate_fn) -> None:
    data = json.loads((_examples_dir() / name).read_text(encoding="utf-8"))
    r1 = validate_fn(data)
    r2 = validate_fn(data)
    assert r1.ok and r2.ok
    assert r1.digest == r2.digest


def test_cross_standard_capability_id_consistency_in_examples() -> None:
    """Examples intentionally share capability_id across policy and delegation graph."""
    cap = json.loads((_examples_dir() / "capability_policy.valid.json").read_text(encoding="utf-8"))
    dg = json.loads((_examples_dir() / "delegation_graph.valid.json").read_text(encoding="utf-8"))
    cap_ids = {c["capability_id"] for c in cap["capabilities"]}
    edge_caps = {e["capability_id"] for e in dg["edges"]}
    assert cap_ids & edge_caps


def test_raw_content_field_rejected_across_standards() -> None:
    for fname, mutate in [
        (
            "capability_policy.valid.json",
            lambda d: d["capabilities"][0].update({"prompt": "x"}) or d,
        ),
        ("delegation_graph.valid.json", lambda d: d.update({"message_body": "x"}) or d),
        ("trace_verification_plan.valid.json", lambda d: d.update({"output_text": "x"}) or d),
        ("governance_evidence_pack.valid.json", lambda d: d.update({"input_text": "x"}) or d),
    ]:
        data = json.loads((_examples_dir() / fname).read_text(encoding="utf-8"))
        mutate(data)
        if fname.startswith("capability"):
            r = validate_capability_policy_document(data)
        elif fname.startswith("delegation"):
            r = validate_delegation_graph_document(data)
        elif fname.startswith("trace"):
            r = validate_trace_verification_plan_document(data)
        else:
            r = validate_governance_evidence_pack_document(data)
        assert not r.ok
        assert any(i.code == "raw_field_rejected" for i in r.issues)


def test_cli_validates_all_examples() -> None:
    mapping = [
        ("validate-capability-policy", "capability_policy.valid.json"),
        ("validate-delegation-graph", "delegation_graph.valid.json"),
        ("validate-trace-verification-plan", "trace_verification_plan.valid.json"),
        ("validate-evidence-pack", "governance_evidence_pack.valid.json"),
    ]
    for cmd, fname in mapping:
        cp = subprocess.run(
            [sys.executable, "-m", "aigov_py.standards.cli", cmd, str(_examples_dir() / fname)],
            cwd=str(_repo_root() / "python"),
            capture_output=True,
            text=True,
            check=False,
        )
        assert cp.returncode == 0, cp.stdout + cp.stderr
