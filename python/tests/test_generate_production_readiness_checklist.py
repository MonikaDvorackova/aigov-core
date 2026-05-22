"""Tests for scripts/generate_production_readiness_checklist.py."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "docs/operations/customer-operations-manifest.json"


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_production_readiness_checklist.py"
    spec = importlib.util.spec_from_file_location("generate_production_readiness_checklist", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gen_mod():
    return _load_mod()


def test_generate_markdown_deterministic(gen_mod):
    a = gen_mod.generate_markdown(REPO_ROOT, MANIFEST)
    b = gen_mod.generate_markdown(REPO_ROOT, MANIFEST)
    assert a == b
    assert "## Deployment prerequisites" in a
    assert "## Environment variables" in a
    assert "## Readiness probes" in a
    assert "## Evidence flow" in a
    assert "## Support contacts" in a
    assert "## Incident escalation" in a
    assert "## SLO / SLA checks" in a
    assert "## Renewal handoff" in a


def test_generate_markdown_writes_file(gen_mod, tmp_path: Path):
    out = tmp_path / "out.md"
    # Exercise CLI --out path (subprocess).
    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "generate_production_readiness_checklist.py"),
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
    text = out.read_text(encoding="utf-8")
    assert text == gen_mod.generate_markdown(REPO_ROOT, MANIFEST)


def test_subprocess_stdout_matches_module(gen_mod):
    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "generate_production_readiness_checklist.py"),
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
