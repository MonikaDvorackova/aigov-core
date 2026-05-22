from __future__ import annotations

import json
from pathlib import Path

from aigov_py.standards.common import canonical_json
from aigov_py.standards.evaluation import evaluate_standards_corpus, evaluation_json


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_evaluation_corpus_all_valid_deterministic() -> None:
    r1 = evaluate_standards_corpus(repo_root=_repo_root())
    r2 = evaluate_standards_corpus(repo_root=_repo_root())
    assert r1 == r2
    assert r1["verdict"] == "VALID"
    assert r1["total_documents"] == 7
    assert r1["valid_documents"] == 7
    assert r1["invalid_documents"] == 0
    assert r1["digest_stability"] is True
    assert r1["issue_count"] == 0
    assert r1["validators"] == [
        "validate_capability_policy_document",
        "validate_delegation_graph_document",
        "validate_trace_verification_plan_document",
        "validate_governance_evidence_pack_document",
        "validate_governance_evidence_pack_document",
        "validate_governance_policy_module_document",
        "validate_governance_decision_trace_document",
    ]
    j1 = evaluation_json(repo_root=_repo_root())
    j2 = evaluation_json(repo_root=_repo_root())
    assert j1 == j2
    assert j1 == canonical_json(json.loads(j1))
