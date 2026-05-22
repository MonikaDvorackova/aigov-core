"""Tests for scripts/public_launch_readiness_score.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "public_launch_readiness_score.py"
    spec = importlib.util.spec_from_file_location("public_launch_readiness_score", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_mod()


def test_sample_snapshot_scores(mod):
    payload, code = mod.compute_score(REPO_ROOT, "examples/launch/sample-standardization-readiness-snapshot.json")
    required = (
        "ok",
        "launch_readiness_score",
        "standardization_score",
        "documentation_score",
        "ecosystem_score",
        "certification_score",
        "risk_level",
        "findings",
        "recommendations",
    )
    for k in required:
        assert k in payload
    assert list(json.loads(json.dumps(payload, sort_keys=True)).keys()) == sorted(payload.keys())
    assert code == 0
    assert payload["ok"] is True


def test_invalid_snapshot_returns_zero_scores(mod, tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    payload, code = mod.compute_score(tmp_path, "bad.json")
    assert code == 1
    assert payload["ok"] is False
    assert payload["launch_readiness_score"] == 0
