from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from aigov_py.standards.trace_verification import (
    digest_trace_verification_plan_document,
    trace_verification_plan_document_from_dict,
    validate_trace_verification_plan_document,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _example() -> dict:
    p = _repo_root() / "examples" / "standards" / "trace_verification_plan.valid.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_trace_plan_example_valid() -> None:
    res = validate_trace_verification_plan_document(_example())
    assert res.ok
    assert res.digest is not None


def test_trace_plan_plan_digest_mismatch() -> None:
    doc = _example()
    doc["plan_digest"] = "sha256:" + "b" * 64
    res = validate_trace_verification_plan_document(doc)
    assert not res.ok
    assert any(i.code == "plan_digest_mismatch" for i in res.issues)


def test_trace_plan_finding_unknown_requirement() -> None:
    doc = _example()
    doc["findings"][0]["requirement_id"] = "req.missing"
    res = validate_trace_verification_plan_document(doc)
    assert not res.ok


def test_trace_plan_invalid_status() -> None:
    doc = _example()
    doc["findings"][0]["status"] = "MAYBE"
    res = validate_trace_verification_plan_document(doc)
    assert not res.ok


def test_trace_plan_duplicate_requirement_id() -> None:
    doc = _example()
    doc["requirements"] = list(doc["requirements"]) + [
        {"requirement_id": "req.chain", "description": "dup"}
    ]
    res = validate_trace_verification_plan_document(doc)
    assert not res.ok


def test_trace_plan_digest_stable_without_optional_field_in_input() -> None:
    doc = copy.deepcopy(_example())
    del doc["plan_digest"]
    doc_tv, issues = trace_verification_plan_document_from_dict(doc)
    assert doc_tv is not None
    assert not issues
    d = digest_trace_verification_plan_document(doc_tv)
    res = validate_trace_verification_plan_document(doc)
    assert res.ok
    assert res.digest == d


def test_trace_plan_raw_field_rejected() -> None:
    doc = _example()
    doc["input_text"] = "nope"
    res = validate_trace_verification_plan_document(doc)
    assert not res.ok
