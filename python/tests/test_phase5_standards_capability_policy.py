from __future__ import annotations

import copy
import json
from pathlib import Path

from aigov_py.standards.capability_policy import (
    digest_capability_policy_document,
    validate_capability_policy_document,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _example() -> dict:
    p = _repo_root() / "examples" / "standards" / "capability_policy.valid.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_capability_policy_example_valid() -> None:
    doc = _example()
    res = validate_capability_policy_document(doc)
    assert res.ok
    assert res.digest is not None
    assert res.digest.startswith("sha256:")


def test_capability_policy_digest_changes_when_policy_id_changes() -> None:
    doc = _example()
    res1 = validate_capability_policy_document(doc)
    doc2 = copy.deepcopy(doc)
    doc2["policy_id"] = "pol.other"
    res2 = validate_capability_policy_document(doc2)
    assert res1.digest != res2.digest


def test_capability_policy_duplicate_capability_id() -> None:
    doc = _example()
    doc["capabilities"] = list(doc["capabilities"]) + [
        {
            "capability_id": "cap.read_docs",
            "name": "Dup",
            "description": "Dup",
            "risk_class": "MINIMAL",
            "allowed_tools": ["t1"],
            "constraints": [],
            "evidence_requirements": ["ev.1"],
            "ai_act_refs": [],
        }
    ]
    res = validate_capability_policy_document(doc)
    assert not res.ok
    assert any(i.code == "capability_id_duplicate" for i in res.issues)


def test_capability_policy_invalid_risk_class() -> None:
    doc = _example()
    doc["capabilities"][0]["risk_class"] = "UNKNOWN"
    res = validate_capability_policy_document(doc)
    assert not res.ok


def test_capability_policy_empty_allowed_tool() -> None:
    doc = _example()
    doc["capabilities"][0]["allowed_tools"] = ["ok", "  "]
    res = validate_capability_policy_document(doc)
    assert not res.ok


def test_capability_policy_raw_prompt_field_rejected() -> None:
    doc = _example()
    doc["capabilities"][0]["prompt"] = "secret"
    res = validate_capability_policy_document(doc)
    assert not res.ok
    assert any(i.code == "raw_field_rejected" for i in res.issues)


def test_digest_determinism_parsed_document() -> None:
    from aigov_py.standards.capability_policy import capability_policy_document_from_dict

    doc, issues = capability_policy_document_from_dict(_example())
    assert doc is not None
    assert not issues
    d1 = digest_capability_policy_document(doc)
    d2 = digest_capability_policy_document(doc)
    assert d1 == d2
