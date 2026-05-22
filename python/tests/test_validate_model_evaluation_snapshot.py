"""Tests for scripts/validate_model_evaluation_snapshot.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_model_evaluation_snapshot.py"
    spec = importlib.util.spec_from_file_location("validate_model_evaluation_snapshot", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_mod()


def test_validate_sample_snapshot(mod):
    rel = "examples/model-risk/sample-model-evaluation-snapshot.json"
    payload, code = mod.validate_snapshot(REPO_ROOT, rel)
    assert code == 0
    assert payload["ok"] is True
    raw = mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_validate_missing_snapshot(mod, tmp_path: Path):
    payload, code = mod.validate_snapshot(tmp_path, "examples/model-risk/sample-model-evaluation-snapshot.json")
    assert code == 1
    assert payload["ok"] is False


def test_validate_missing_top_level(mod, tmp_path: Path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    payload, code = mod.validate_snapshot(tmp_path, "s.json")
    assert code == 1
    assert any("missing_required_key" in e for e in payload["errors"])
