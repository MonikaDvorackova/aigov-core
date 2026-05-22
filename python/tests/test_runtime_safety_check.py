"""Tests for scripts/runtime_safety_check.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "runtime_safety_check.py"
    spec = importlib.util.spec_from_file_location("runtime_safety_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def chk_mod():
    return _load_mod()


def test_run_check_real_repo(chk_mod):
    payload, code = chk_mod.run_check(
        REPO_ROOT,
        "docs/runtime-safety/runtime-safety-manifest.json",
        "examples/runtime-safety/sample-runtime-safety-snapshot.json",
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    names = sorted(c["name"] for c in payload["checks"])
    assert names == sorted(
        [
            "documentation_paths",
            "example_drivers",
            "makefile_wiring",
            "manifest_validation",
            "runtime_safety_score",
            "snapshot_validation",
        ]
    )
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    assert payload["checks"] == sorted(payload["checks"], key=lambda c: c["name"])
    assert not payload["failures"]


def test_run_check_missing_paths(chk_mod, tmp_path: Path):
    payload, code = chk_mod.run_check(
        tmp_path,
        "docs/runtime-safety/runtime-safety-manifest.json",
        "examples/runtime-safety/sample-runtime-safety-snapshot.json",
    )
    assert code == 1
    assert payload["ok"] is False
