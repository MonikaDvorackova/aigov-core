"""Tests for scripts/generate_operational_intelligence_report.py."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_operational_intelligence_report.py"
    spec = importlib.util.spec_from_file_location("generate_operational_intelligence_report", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gen_mod():
    return _load_mod()


def test_generate_markdown_structure(gen_mod):
    md = gen_mod.generate_markdown(
        REPO_ROOT,
        "examples/observability/sample-operational-snapshot.json",
        "docs/observability/observability-manifest.json",
    )
    assert md.startswith("# GovAI operational intelligence report\n")
    assert "## Snapshot metadata" in md
    assert "## Scores" in md
    assert "## Runtime health" in md
    assert "## Readiness" in md
    assert "## Evidence flow" in md
    assert "## Diagnostics" in md
    assert "## Findings" in md
    assert "## Report metadata" in md
    assert md.endswith("\n")


def test_generate_markdown_stable_digest(gen_mod):
    md = gen_mod.generate_markdown(
        REPO_ROOT,
        "examples/observability/sample-operational-snapshot.json",
        "docs/observability/observability-manifest.json",
    )
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == "66e9e056ea087b7fb270f0c1ceb57264b236b74413d0168715010b304e871d1e"


def test_generate_markdown_missing_snapshot(gen_mod, tmp_path: Path):
    with pytest.raises((FileNotFoundError, OSError)):
        gen_mod.generate_markdown(tmp_path, "missing.json", "missing-manifest.json")
