"""Tests for scripts/validate_changelog.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_changelog.py"
    spec = importlib.util.spec_from_file_location("validate_changelog", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def changelog_mod():
    return _load_mod()


def test_real_repo_passes(changelog_mod):
    payload, code = changelog_mod.compute_changelog_validation(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["latest_released"] == "0.2.1"
    assert payload["has_unreleased"] is True
    raw = changelog_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_missing_changelog_fails(changelog_mod, tmp_path: Path):
    payload, code = changelog_mod.compute_changelog_validation(tmp_path)
    assert code == 1
    assert payload["ok"] is False
    assert "missing_changelog" in payload["failures"]
