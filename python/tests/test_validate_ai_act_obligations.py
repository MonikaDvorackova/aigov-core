"""Tests for scripts/validate_ai_act_obligations.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_ai_act_obligations.py"
    spec = importlib.util.spec_from_file_location("validate_ai_act_obligations", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vao_mod():
    return _load_mod()


def test_validate_real_obligations(vao_mod):
    rel = "docs/regulatory/ai-act-obligations.json"
    payload, code = vao_mod.validate_obligations(REPO_ROOT, rel)
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    raw = vao_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_validate_missing_file(vao_mod, tmp_path: Path):
    payload, code = vao_mod.validate_obligations(tmp_path, "docs/regulatory/ai-act-obligations.json")
    assert code == 1
    assert payload["ok"] is False


def test_duplicate_obligation_id(vao_mod, tmp_path: Path):
    p = tmp_path / "o.json"
    p.write_text(
        json.dumps(
            {
                "obligations": [
                    {
                        "article_reference": "A1",
                        "category": "other",
                        "evidence_paths": ["x.md"],
                        "govai_mapping": "Mapping text long enough for validation rules.",
                        "id": "dup",
                        "summary": "Summary text long enough for validation rules.",
                        "title": "T",
                    },
                    {
                        "article_reference": "A2",
                        "category": "other",
                        "evidence_paths": ["x.md"],
                        "govai_mapping": "Second mapping text long enough for validation.",
                        "id": "dup",
                        "summary": "Another summary text long enough for validation.",
                        "title": "T2",
                    },
                ],
                "summary": "Root summary text long enough for validation.",
                "version": 1,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "x.md").write_text("# x\n", encoding="utf-8")
    payload, code = vao_mod.validate_obligations(tmp_path, "o.json")
    assert code == 1
    assert any("duplicate_obligation_id" in e for e in payload["errors"])


def test_invalid_category(vao_mod, tmp_path: Path):
    p = tmp_path / "o.json"
    p.write_text(
        json.dumps(
            {
                "obligations": [
                    {
                        "article_reference": "A1",
                        "category": "not_a_real_category",
                        "evidence_paths": ["x.md"],
                        "govai_mapping": "Mapping text long enough for validation rules.",
                        "id": "o1",
                        "summary": "Summary text long enough for validation rules.",
                        "title": "T",
                    }
                ],
                "summary": "Root summary text long enough for validation.",
                "version": 1,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "x.md").write_text("# x\n", encoding="utf-8")
    payload, code = vao_mod.validate_obligations(tmp_path, "o.json")
    assert code == 1
    assert any("obligation_invalid_category" in e for e in payload["errors"])
