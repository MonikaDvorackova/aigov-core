"""Tests for scripts/validate_runtime_safety_manifest.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_runtime_safety_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_runtime_safety_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vmod():
    return _load_mod()


def test_validate_real_manifest(vmod):
    payload, code = vmod.validate_manifest(REPO_ROOT, "docs/runtime-safety/runtime-safety-manifest.json")
    assert code == 0
    assert payload["ok"] is True
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = vmod.dumps_json(payload)
    assert '"ok":true' in raw or ":true" in raw


def test_validate_missing_manifest(vmod, tmp_path: Path):
    payload, code = vmod.validate_manifest(tmp_path, "docs/nope.json")
    assert code == 1
    assert payload["ok"] is False
