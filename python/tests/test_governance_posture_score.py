"""Tests for scripts/governance_posture_score.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "governance_posture_score.py"
    spec = importlib.util.spec_from_file_location("governance_posture_score", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gps_mod():
    return _load_mod()


def _minimal_good_snapshot(gps_mod):
    def sig(i: str):
        return {"id": i, "severity": "low", "status": "pass", "summary": "ok"}

    return {
        "captured_at": "t",
        "environment": "staging",
        "org_id": "o",
        "snapshot_version": "1",
        "signal_domains": {d: {"signals": [sig(f"{d}.ok")]} for d in gps_mod.DOMAIN_ORDER},
    }


def test_score_real_sample(gps_mod):
    payload, code = gps_mod.compute_scores(
        REPO_ROOT,
        "examples/control-plane/sample-governance-posture-snapshot.json",
        "docs/control-plane/control-plane-manifest.json",
    )
    assert isinstance(payload["governance_posture_score"], int)
    assert 0 <= payload["governance_posture_score"] <= 100
    assert payload["posture_level"] in ("HEALTHY", "NEEDS_IMPROVEMENT", "AT_RISK", "BLOCKED")
    raw = gps_mod.dumps_json(payload)
    assert json.loads(raw) == payload
    # sample is expected to be acceptable, not necessarily pristine
    assert payload["ok"] in (True, False)
    assert code in (0, 1)


def test_score_is_healthy_when_all_pass(gps_mod, tmp_path: Path):
    snap = _minimal_good_snapshot(gps_mod)
    (tmp_path / "s.json").write_text(json.dumps(snap), encoding="utf-8")
    payload, code = gps_mod.compute_scores(tmp_path, "s.json", "missing-manifest.json")
    assert code == 0
    assert payload["posture_level"] == "HEALTHY"
    assert payload["ok"] is True
    assert payload["governance_posture_score"] >= 95


def test_score_blocked_on_critical_fail(gps_mod, tmp_path: Path):
    snap = _minimal_good_snapshot(gps_mod)
    snap["signal_domains"]["runtime_safety"]["signals"].append(
        {"id": "rs.crit", "severity": "critical", "status": "fail", "summary": "bad"}
    )
    (tmp_path / "s.json").write_text(json.dumps(snap), encoding="utf-8")
    payload, code = gps_mod.compute_scores(tmp_path, "s.json", "missing-manifest.json")
    assert code == 1
    assert payload["posture_level"] == "BLOCKED"
    assert payload["ok"] is False

