"""Tests for scripts/public_launch_check.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "public_launch_check.py"
    spec = importlib.util.spec_from_file_location("public_launch_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_mod()


def test_run_checks_real_repo(mod):
    payload = mod.run_checks(REPO_ROOT)
    assert "checks" in payload
    assert "checked_paths" in payload
    assert "failures" in payload
    assert "ok" in payload
    assert "score" in payload
    assert "warnings" in payload
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    assert payload["ok"] is True
    assert payload["score"] >= 85


def test_json_roundtrip(mod):
    payload = mod.run_checks(REPO_ROOT)
    raw = mod.dumps_json(payload)
    assert json.loads(raw) == payload
