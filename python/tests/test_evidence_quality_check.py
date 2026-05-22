"""Tests for scripts/evidence_quality_check.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "evidence_quality_check.py"
    spec = importlib.util.spec_from_file_location("evidence_quality_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def eq_mod():
    return _load_mod()


def test_compute_evidence_quality_real_repo(eq_mod):
    payload, code = eq_mod.compute_evidence_quality(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert payload["version"] == 1
    assert payload["failures"] == []
    assert payload["warnings"] == []
    assert set(payload.keys()) == {
        "checked_paths",
        "checks",
        "failures",
        "ok",
        "score",
        "version",
        "warnings",
    }
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = eq_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_compute_evidence_quality_missing(eq_mod, tmp_path: Path):
    payload, code = eq_mod.compute_evidence_quality(tmp_path)
    assert code == 1
    assert payload["ok"] is False
