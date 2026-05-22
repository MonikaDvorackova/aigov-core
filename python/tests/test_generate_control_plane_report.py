"""Tests for scripts/generate_control_plane_report.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_control_plane_report.py"
    spec = importlib.util.spec_from_file_location("generate_control_plane_report", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gcpr_mod():
    return _load_mod()


def test_report_contains_expected_sections(gcpr_mod):
    snap = json.loads((REPO_ROOT / "examples/control-plane/sample-governance-posture-snapshot.json").read_text(encoding="utf-8"))
    md = gcpr_mod.render_report(snap, "examples/control-plane/sample-governance-posture-snapshot.json")
    assert "# Autonomous governance control plane report" in md
    assert "## Governance posture" in md
    assert "## Domain scores" in md
    assert "## Findings" in md
    assert "## Recommendations" in md

