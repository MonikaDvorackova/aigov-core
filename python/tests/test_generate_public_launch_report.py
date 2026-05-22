"""Tests for scripts/generate_public_launch_report.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_public_launch_report.py"
    spec = importlib.util.spec_from_file_location("generate_public_launch_report", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_mod()


def test_generate_markdown_stable(mod):
    md1 = mod.generate_markdown(
        REPO_ROOT,
        "examples/launch/sample-standardization-readiness-snapshot.json",
        "docs/launch/public-launch-manifest.json",
    )
    md2 = mod.generate_markdown(
        REPO_ROOT,
        "examples/launch/sample-standardization-readiness-snapshot.json",
        "docs/launch/public-launch-manifest.json",
    )
    assert md1 == md2
    assert "# GovAI public launch report" in md1
    assert "## Readiness scores" in md1


def test_generate_writes_file(tmp_path: Path):
    import subprocess

    out = tmp_path / "out.md"
    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "generate_public_launch_report.py"),
            "--input",
            "examples/launch/sample-standardization-readiness-snapshot.json",
            "--out",
            str(out),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert out.is_file()
    assert "GovAI public launch report" in out.read_text(encoding="utf-8")
