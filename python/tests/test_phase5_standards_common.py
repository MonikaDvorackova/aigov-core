from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys

from aigov_py.standards.common import (
    StandardsLoadError,
    ValidationIssue,
    ValidationResult,
    canonical_digest,
    canonical_json,
    find_raw_content_fields,
    infer_standards_document_kind,
    load_standard_document,
    normalize_digest_token,
    validate_digest_token,
)


def test_canonical_json_deterministic_key_sorting() -> None:
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert canonical_json(a) == canonical_json(b)
    assert canonical_json(a) == '{"a":1,"b":2}'


def test_canonical_digest_deterministic() -> None:
    v1 = {"z": [3, 2, 1], "a": {"b": 1}}
    v2 = {"a": {"b": 1}, "z": [3, 2, 1]}
    assert canonical_digest(v1) == canonical_digest(v2)
    assert canonical_digest(v1).startswith("sha256:")
    assert len(canonical_digest(v1)) == len("sha256:") + 64


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("sha256:" + "A" * 64, "sha256:" + "a" * 64),
        (" " + ("b" * 64) + " ", "sha256:" + "b" * 64),
        ("sha256:" + ("c" * 64), "sha256:" + "c" * 64),
    ],
)
def test_normalize_digest_token(raw: str, expected: str) -> None:
    assert normalize_digest_token(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "sha256:",
        "sha256:xyz",
        "sha256:" + ("a" * 63),
        "sha256:" + ("g" * 64),
        "not-a-digest",
    ],
)
def test_validate_digest_token_rejects_invalid(raw: str) -> None:
    assert validate_digest_token(raw) is False


def test_find_raw_content_fields_rejects_banned_keys_anywhere() -> None:
    doc = {
        "schema_version": "x",
        "nested": {"prompt": "nope"},
        "arr": [{"content": "nope2"}],
    }
    issues = find_raw_content_fields(doc)
    assert any(i.code == "raw_field_rejected" and i.path.endswith(".prompt") for i in issues)
    assert any(i.code == "raw_field_rejected" and i.path.endswith(".content") for i in issues)


def test_validation_result_sorted_issues_stable() -> None:
    res = ValidationResult(
        ok=False,
        issues=(
            ValidationIssue(code="b", message="m2", path="x"),
            ValidationIssue(code="a", message="m1", path="x"),
            ValidationIssue(code="a", message="m0", path="a"),
        ),
    )
    sorted_ = res.sorted_issues()
    assert [i.path for i in sorted_] == ["a", "x", "x"]
    assert [(i.code, i.message) for i in sorted_[1:]] == [("a", "m1"), ("b", "m2")]


def test_load_standard_document_json(tmp_path: Path) -> None:
    p = tmp_path / "doc.json"
    p.write_text('{"a":1,"b":[3,2]}', encoding="utf-8")
    assert load_standard_document(p) == {"a": 1, "b": [3, 2]}


def test_load_standard_document_missing_raises() -> None:
    with pytest.raises(StandardsLoadError) as ei:
        load_standard_document("/nonexistent/path/doc.json")
    assert ei.value.code == "file_not_found"


def test_load_standard_document_unsupported_extension_raises(tmp_path: Path) -> None:
    p = tmp_path / "doc.txt"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(StandardsLoadError) as ei:
        load_standard_document(p)
    assert ei.value.code == "unsupported_format"


@pytest.mark.skipif(sys.platform.startswith("win"), reason="chmod 000 not portable on Windows")
def test_load_standard_document_unreadable_returns_read_failed(tmp_path: Path) -> None:
    p = tmp_path / "sec.json"
    p.write_text("{}", encoding="utf-8")
    p.chmod(0o000)
    try:
        with pytest.raises(StandardsLoadError) as ei:
            load_standard_document(p)
        assert ei.value.code == "read_failed"
    finally:
        p.chmod(0o644)


def test_infer_standards_document_kind_examples() -> None:
    root = Path(__file__).resolve().parents[2] / "examples" / "standards"
    assert infer_standards_document_kind(load_standard_document(root / "capability_policy.valid.json")) == "capability-policy"
    assert infer_standards_document_kind(load_standard_document(root / "delegation_graph.valid.json")) == "delegation-graph"
    assert infer_standards_document_kind(load_standard_document(root / "trace_verification_plan.valid.json")) == "trace-verification-plan"
    assert infer_standards_document_kind(load_standard_document(root / "governance_evidence_pack.valid.json")) == "evidence-pack"

