"""Tests for scripts/model_risk_score.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "model_risk_score.py"
    spec = importlib.util.spec_from_file_location("model_risk_score", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_mod()


def test_compute_score_sample(mod):
    payload, code = mod.compute_score(
        REPO_ROOT,
        "examples/model-risk/sample-model-evaluation-snapshot.json",
        "docs/model-risk/model-risk-manifest.json",
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["model_risk_score"] == 85
    assert payload["assurance_level"] == "L3"
    assert payload["evaluation_score"] == 100
    assert payload["safety_score"] == 70
    assert payload["robustness_score"] == 86
    assert payload["fairness_score"] == 83
    keys = {
        "assurance_level",
        "evaluation_score",
        "fairness_score",
        "findings",
        "manifest_path",
        "model_risk_score",
        "ok",
        "recommendations",
        "robustness_score",
        "safety_score",
        "snapshot_path",
        "version",
        "weights",
    }
    assert set(payload.keys()) == keys


def test_compute_score_invalid_snapshot(mod, tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    payload, code = mod.compute_score(tmp_path, "bad.json", "docs/model-risk/model-risk-manifest.json")
    assert code == 1
    assert payload["ok"] is False
    assert payload["model_risk_score"] == 0
