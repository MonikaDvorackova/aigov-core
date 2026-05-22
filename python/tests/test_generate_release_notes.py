"""Tests for scripts/generate_release_notes.py."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_release_notes.py"
    spec = importlib.util.spec_from_file_location("generate_release_notes", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def grn_mod():
    return _load_mod()


def test_deterministic_markdown_matches_sample(grn_mod):
    expected = (REPO_ROOT / "examples/releases/sample-generated-release-notes-1.0.0.md").read_text(encoding="utf-8")
    got = grn_mod.generate_notes(REPO_ROOT, "1.0.0", "CHANGELOG.md")
    assert got == expected


def test_normalize_version_accepts_v_prefix(grn_mod):
    a = grn_mod.generate_notes(REPO_ROOT, "v1.0.0", "CHANGELOG.md")
    b = grn_mod.generate_notes(REPO_ROOT, "1.0.0", "CHANGELOG.md")
    assert a == b


def test_subprocess_generate_release_notes(tmp_path: Path):
    out = tmp_path / "out.md"
    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "generate_release_notes.py"),
            "--version",
            "1.0.0",
            "--out",
            str(out),
            "--repo-root",
            str(REPO_ROOT),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert out.is_file()
    assert "# GovAI 1.0.0" in out.read_text(encoding="utf-8")
