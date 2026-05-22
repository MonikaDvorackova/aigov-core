"""Tests for scripts/generate_partner_certification_package.py."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "docs/partners/partner-ecosystem-manifest.json"


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_partner_certification_package.py"
    spec = importlib.util.spec_from_file_location("generate_partner_certification_package", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gen_mod():
    return _load_mod()


def test_generate_deterministic_twice(gen_mod):
    a = gen_mod.generate_markdown(REPO_ROOT, MANIFEST)
    b = gen_mod.generate_markdown(REPO_ROOT, MANIFEST)
    assert a == b
    assert "## Partner program overview" in a
    assert "## Certification levels" in a
    assert "## Renewal requirements" in a


def test_generate_subprocess_stdout_matches_module(gen_mod, tmp_path: Path):
    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "generate_partner_certification_package.py"),
            "--manifest",
            MANIFEST,
            "--repo-root",
            str(REPO_ROOT),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert r.stdout == gen_mod.generate_markdown(REPO_ROOT, MANIFEST)


def test_generate_out_file(gen_mod, tmp_path: Path):
    out = tmp_path / "pkg.md"
    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "generate_partner_certification_package.py"),
            "--manifest",
            MANIFEST,
            "--repo-root",
            str(REPO_ROOT),
            "--out",
            str(out),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert r.stdout == ""
    assert out.read_text(encoding="utf-8") == gen_mod.generate_markdown(REPO_ROOT, MANIFEST)
