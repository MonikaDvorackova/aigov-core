"""Tests for scripts/validate_iso_42001_clause_index.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_iso_42001_clause_index.py"
    spec = importlib.util.spec_from_file_location("validate_iso_42001_clause_index", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_mod()


def test_validate_real_clause_index(mod):
    rel = "docs/standards/iso-42001-clause-index.json"
    payload, code = mod.validate_clause_index(REPO_ROOT, rel)
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    assert payload["failures"] == []
    raw = mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_validate_missing_index(mod, tmp_path: Path):
    payload, code = mod.validate_clause_index(tmp_path, "docs/standards/iso-42001-clause-index.json")
    assert code == 1
    assert payload["ok"] is False


def test_validate_duplicate_clause_id(mod, tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# doc\n", encoding="utf-8")
    index = {
        "version": 1,
        "summary": "Clause index summary text long enough for validation.",
        "clauses": [
            {
                "id": "dup",
                "clause_reference": "Clause 4",
                "title": "Context",
                "category": "context",
                "summary": "Summary text long enough for validation rules.",
                "evidence_paths": ["doc.md"],
                "govai_mapping": "Mapping narrative long enough for validation.",
            },
            {
                "id": "dup",
                "clause_reference": "Clause 5",
                "title": "Leadership",
                "category": "leadership",
                "summary": "Another summary text long enough for validation.",
                "evidence_paths": ["doc.md"],
                "govai_mapping": "Another mapping narrative for validation.",
            },
        ],
    }
    idx_path = tmp_path / "idx.json"
    idx_path.write_text(json.dumps(index), encoding="utf-8")
    payload, code = mod.validate_clause_index(tmp_path, "idx.json")
    assert code == 1
    assert any("duplicate_clause_id" in e for e in payload["errors"])
