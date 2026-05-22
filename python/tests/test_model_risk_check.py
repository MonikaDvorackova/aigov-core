"""Tests for scripts/model_risk_check.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "model_risk_check.py"
    spec = importlib.util.spec_from_file_location("model_risk_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_mod()


def test_run_check_real_repo(mod):
    payload, code = mod.run_check(
        REPO_ROOT,
        "docs/model-risk/model-risk-manifest.json",
        "examples/model-risk/sample-model-evaluation-snapshot.json",
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 85
    names = sorted(c["name"] for c in payload["checks"])
    assert names == sorted(
        [
            "documentation_paths",
            "example_paths",
            "makefile_wiring",
            "manifest_validation",
            "model_risk_score",
            "snapshot_validation",
        ]
    )
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    assert not payload["failures"]


def test_run_check_missing_paths(mod, tmp_path: Path):
    payload, code = mod.run_check(
        tmp_path,
        "docs/model-risk/model-risk-manifest.json",
        "examples/model-risk/sample-model-evaluation-snapshot.json",
    )
    assert code == 1
    assert payload["ok"] is False
