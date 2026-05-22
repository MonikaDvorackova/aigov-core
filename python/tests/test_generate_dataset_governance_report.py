"""Tests for scripts/generate_dataset_governance_report.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_dataset_governance_report.py"
    spec = importlib.util.spec_from_file_location("generate_dataset_governance_report", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rep_mod():
    return _load_mod()


def test_render_report_stable(rep_mod):
    raw = (REPO_ROOT / "examples/evidence-quality/sample-dataset-provenance-snapshot.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    md1 = rep_mod.render_report(data)
    md2 = rep_mod.render_report(data)
    assert md1 == md2
    assert "## Scores" in md1
    assert "dataset_id" in md1
    assert len(md1.encode("utf-8")) >= 64


def test_render_report_includes_findings(rep_mod):
    raw = (REPO_ROOT / "examples/evidence-quality/sample-dataset-provenance-snapshot.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    md = rep_mod.render_report(data)
    assert "provenance_checksum_coverage_partial" in md
