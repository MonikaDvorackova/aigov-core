from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from aigov_py.standards.evidence_pack import validate_governance_evidence_pack_document


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _example() -> dict:
    p = _repo_root() / "examples" / "standards" / "governance_evidence_pack.valid.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_evidence_pack_example_valid() -> None:
    res = validate_governance_evidence_pack_document(_example())
    assert res.ok
    assert res.digest is not None


def test_evidence_pack_governed_requires_control_refs() -> None:
    doc = _example()
    doc["artifacts"][0]["control_refs"] = []
    res = validate_governance_evidence_pack_document(doc)
    assert not res.ok


def test_evidence_pack_invalid_content_digest() -> None:
    doc = _example()
    doc["artifacts"][0]["content_digest"] = "not-a-digest"
    res = validate_governance_evidence_pack_document(doc)
    assert not res.ok


def test_evidence_pack_digest_manifest_mismatch() -> None:
    doc = _example()
    doc["digest_manifest"]["entries"][0]["artifact_id"] = "wrong.id"
    res = validate_governance_evidence_pack_document(doc)
    assert not res.ok


def test_evidence_pack_pack_digest_mismatch() -> None:
    doc = _example()
    doc["pack_digest"] = "sha256:" + "c" * 64
    res = validate_governance_evidence_pack_document(doc)
    assert not res.ok


def test_evidence_pack_raw_payload_rejected() -> None:
    doc = _example()
    doc["raw_payload"] = {}
    res = validate_governance_evidence_pack_document(doc)
    assert not res.ok
