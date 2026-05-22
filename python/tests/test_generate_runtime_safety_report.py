"""Tests for scripts/generate_runtime_safety_report.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_runtime_safety_report.py"
    spec = importlib.util.spec_from_file_location("generate_runtime_safety_report", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rep_mod():
    return _load_mod()


def test_generate_twice_identical(rep_mod):
    a = rep_mod.generate_markdown(
        REPO_ROOT,
        "examples/runtime-safety/sample-runtime-safety-snapshot.json",
        "docs/runtime-safety/runtime-safety-manifest.json",
    )
    b = rep_mod.generate_markdown(
        REPO_ROOT,
        "examples/runtime-safety/sample-runtime-safety-snapshot.json",
        "docs/runtime-safety/runtime-safety-manifest.json",
    )
    assert a == b
    assert "# GovAI runtime safety" in a
    assert "## Scores" in a
    assert "## Recommendations" in a
