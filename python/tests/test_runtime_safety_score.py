"""Tests for scripts/runtime_safety_score.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "runtime_safety_score.py"
    spec = importlib.util.spec_from_file_location("runtime_safety_score", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rsmod():
    return _load_mod()


REQUIRED_KEYS = frozenset(
    {
        "escalation_score",
        "findings",
        "guardrail_score",
        "human_oversight_score",
        "ok",
        "override_readiness_score",
        "recommendations",
        "risk_level",
        "runtime_safety_score",
    }
)


def test_score_sample_snapshot(rsmod):
    payload, code = rsmod.compute_score(
        REPO_ROOT,
        "examples/runtime-safety/sample-runtime-safety-snapshot.json",
        "docs/runtime-safety/runtime-safety-manifest.json",
    )
    assert code == 0
    assert payload["ok"] is True
    assert set(payload.keys()) == REQUIRED_KEYS
    assert payload["risk_level"] in ("low", "medium")
    for k in (
        "runtime_safety_score",
        "guardrail_score",
        "escalation_score",
        "human_oversight_score",
        "override_readiness_score",
    ):
        assert isinstance(payload[k], int)
        assert 0 <= payload[k] <= 100
    assert isinstance(payload["findings"], list)
    assert isinstance(payload["recommendations"], list)
    raw = rsmod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_score_invalid_snapshot(rsmod, tmp_path: Path):
    (tmp_path / "snap.json").write_text("{}", encoding="utf-8")
    payload, code = rsmod.compute_score(tmp_path, "snap.json", "missing.json")
    assert code == 1
    assert payload["ok"] is False
    assert payload["risk_level"] == "critical"
    assert "snapshot_validation_failed" in payload["findings"]
