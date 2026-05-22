"""Tests for scripts/generate_automation_pack_summary.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PACK = "examples/integrations/sample-automation-pack.json"


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_automation_pack_summary.py"
    spec = importlib.util.spec_from_file_location("generate_automation_pack_summary", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gen_mod():
    return _load_mod()


def _pack_data(gen_mod) -> dict:
    p = REPO_ROOT / SAMPLE_PACK
    return json.loads(p.read_text(encoding="utf-8"))


def test_markdown_deterministic_twice(gen_mod):
    data = _pack_data(gen_mod)
    a = gen_mod.render_markdown(SAMPLE_PACK, data)
    b = gen_mod.render_markdown(SAMPLE_PACK, data)
    assert a == b
    assert a.startswith("# Automation pack summary\n")
    assert "### `doc_gate`" in a
    assert "## Artifacts" in a


def test_subprocess_stdout_matches_module(gen_mod, tmp_path: Path):
    data = _pack_data(gen_mod)
    expected = gen_mod.render_markdown(SAMPLE_PACK, data)
    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "generate_automation_pack_summary.py"),
            "--pack",
            SAMPLE_PACK,
            "--repo-root",
            str(REPO_ROOT),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert r.stdout == expected


def test_out_writes_file(gen_mod, tmp_path: Path):
    out = tmp_path / "out.md"
    data = _pack_data(gen_mod)
    expected = gen_mod.render_markdown(SAMPLE_PACK, data)
    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "generate_automation_pack_summary.py"),
            "--pack",
            SAMPLE_PACK,
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
    assert out.read_text(encoding="utf-8") == expected
