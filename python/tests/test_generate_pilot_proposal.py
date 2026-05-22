"""Tests for scripts/generate_pilot_proposal.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_pilot_proposal.py"
    spec = importlib.util.spec_from_file_location("generate_pilot_proposal", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gp_mod():
    return _load_mod()


def test_generate_markdown_deterministic(gp_mod):
    manifest = json.loads((REPO_ROOT / "docs/revenue/revenue-manifest.json").read_text(encoding="utf-8"))
    pilot = json.loads((REPO_ROOT / "examples/pilot-execution/sample-pilot-plan.json").read_text(encoding="utf-8"))
    a = gp_mod.generate_markdown(manifest, pilot)
    b = gp_mod.generate_markdown(manifest, pilot)
    assert a == b
    assert "## Executive summary" in a
    assert "## Conversion criteria" in a


def test_subprocess_writes_file(gp_mod, tmp_path: Path):
    out = tmp_path / "p.md"
    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "generate_pilot_proposal.py"),
            "--manifest",
            str(REPO_ROOT / "docs/revenue/revenue-manifest.json"),
            "--pilot-plan",
            str(REPO_ROOT / "examples/pilot-execution/sample-pilot-plan.json"),
            "--out",
            str(out),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "Pilot proposal" in text
    _ = gp_mod  # use fixture
