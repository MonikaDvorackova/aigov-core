"""Tests for scripts/generate_governance_control_report.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_governance_control_report.py"
    spec = importlib.util.spec_from_file_location("generate_governance_control_report", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gcr_mod():
    return _load_mod()


def test_render_report_sample(gcr_mod):
    raw = (REPO_ROOT / "examples/policy-intelligence/sample-governance-control-snapshot.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    md = gcr_mod.render_report(data)
    assert "## Scores" in md
    assert "## Findings" in md
    assert "## Recommendations" in md
    assert "org_govai_sample" in md
    assert "| Policy coverage | 64 |" in md
    assert "| Control maturity | 56 |" in md
    assert "| Gap risk | 28 |" in md


def test_render_report_invalid(gcr_mod):
    md = gcr_mod.render_report({})
    assert "Input validation failed" in md


def test_subprocess_stdout(gcr_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "generate_governance_control_report.py"),
            "--input",
            str(REPO_ROOT / "examples/policy-intelligence/sample-governance-control-snapshot.json"),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert "# Governance control report" in r.stdout
