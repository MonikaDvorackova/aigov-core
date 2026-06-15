"""Tests for scripts/release_readiness_report.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "release_readiness_report.py"
    spec = importlib.util.spec_from_file_location("release_readiness_report", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def readiness_mod():
    return _load_mod()


def test_real_repo_passes(readiness_mod):
    payload, code = readiness_mod.compute_release_readiness(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert payload["failures"] == []
    raw = readiness_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_missing_makefile_target_fails(readiness_mod, tmp_path: Path):
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n\n## [0.2.1] - 2026-06-10\n", encoding="utf-8")
    payload, code = readiness_mod.compute_release_readiness(tmp_path)
    assert code == 1
    assert payload["ok"] is False
