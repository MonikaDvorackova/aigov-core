"""Tests for scripts/validate_governance_posture_snapshot.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_governance_posture_snapshot.py"
    spec = importlib.util.spec_from_file_location("validate_governance_posture_snapshot", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vgps_mod():
    return _load_mod()


def test_validate_real_sample(vgps_mod):
    payload, code = vgps_mod.validate_snapshot(REPO_ROOT, "examples/control-plane/sample-governance-posture-snapshot.json")
    assert payload["ok"] is True
    assert code == 0
    raw = vgps_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_fails_when_missing_domains(vgps_mod, tmp_path: Path):
    snap = {
        "captured_at": "t",
        "environment": "staging",
        "org_id": "o",
        "signal_domains": {"policy_intelligence": {"signals": [{"id": "x", "severity": "low", "status": "pass", "summary": "s"}]}},
        "snapshot_version": "1",
    }
    (tmp_path / "s.json").write_text(json.dumps(snap), encoding="utf-8")
    payload, code = vgps_mod.validate_snapshot(tmp_path, "s.json")
    assert code == 1
    assert payload["ok"] is False
    assert any(e.startswith("signal_domains_missing_required:") for e in payload["errors"])

