from __future__ import annotations

import json
from pathlib import Path

import pytest

from aigov_py.standards.registry import (
    GOVERNANCE_STANDARDS_REGISTRY,
    validator_for_schema_version,
)

_REPO = Path(__file__).resolve().parents[2]
_EXAMPLES = _REPO / "examples" / "standards"


@pytest.mark.parametrize(
    "schema_version,example_file",
    [
        ("govai.standards.governance_evidence_pack.v1", "evidence-pack.valid.json"),
        ("govai.standards.governance_policy_module.v1", "policy-module.valid.json"),
        ("govai.standards.governance_decision_trace.v1", "decision-trace.valid.json"),
        ("govai.standards.delegation_graph.v1", "delegation_graph.valid.json"),
        ("govai.standards.capability_policy.v1", "capability_policy.valid.json"),
        ("govai.standards.trace_verification_plan.v1", "trace_verification_plan.valid.json"),
    ],
)
def test_registry_validator_dispatch(schema_version: str, example_file: str) -> None:
    validator = validator_for_schema_version(schema_version)
    assert validator is not None, schema_version
    data = json.loads((_EXAMPLES / example_file).read_text(encoding="utf-8"))
    assert data["schema_version"] == schema_version
    result = validator(data)
    assert result.ok, (schema_version, example_file, result.failures)


def test_registry_covers_all_rows() -> None:
    versions = {row.schema_version for row in GOVERNANCE_STANDARDS_REGISTRY}
    assert len(versions) == len(GOVERNANCE_STANDARDS_REGISTRY)
    for version in versions:
        assert validator_for_schema_version(version) is not None
