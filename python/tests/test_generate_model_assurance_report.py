"""Tests for scripts/generate_model_assurance_report.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_model_assurance_report.py"
    spec = importlib.util.spec_from_file_location("generate_model_assurance_report", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_mod()


def test_generate_markdown_sample(mod):
    md = mod.generate_markdown(
        REPO_ROOT,
        "examples/model-risk/sample-model-evaluation-snapshot.json",
        "docs/model-risk/model-risk-manifest.json",
    )
    assert md.startswith("# GovAI model assurance report")
    assert "model_risk_score: `85`" in md
    assert "## Safety pillar (snapshot)" in md
    assert "govai-text-assistant-demo" in md


def test_generate_markdown_missing_snapshot(mod, tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        mod.generate_markdown(tmp_path, "missing.json", "docs/model-risk/model-risk-manifest.json")
