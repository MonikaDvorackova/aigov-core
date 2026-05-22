"""Tests for scripts/operational_health_score.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "operational_health_score.py"
    spec = importlib.util.spec_from_file_location("operational_health_score", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ohs_mod():
    return _load_mod()


def _good_snapshot() -> dict:
    return {
        "captured_at": "2026-05-12T15:30:00Z",
        "diagnostics": {
            "checks": [{"detail": "ok", "name": "x", "ok": True}],
            "failure_count": 0,
            "summary": "Snapshot diagnostics summary long enough for validation.",
            "warning_count": 0,
        },
        "environment": "staging",
        "evidence_flow": {
            "compliance_summary_decision_distribution": {
                "blocked": 1,
                "invalid": 0,
                "valid": 99,
            },
            "evidence_arrival_latency_p95_seconds": 1,
            "evidence_arrival_success_rate_percent": 99,
            "submissions_observed": 100,
        },
        "readiness": {
            "audit_ready_endpoint_status": True,
            "migration_state_consistent": True,
            "policy_pack_load_status": True,
        },
        "runtime_health": {
            "audit_service_uptime_minutes": 1440,
            "error_rate_percent": 0,
            "open_incidents_count": 0,
        },
        "schema_version": 1,
        "snapshot_id": "snap1",
        "window_minutes": 60,
    }


def test_score_real_sample(ohs_mod):
    payload, code = ohs_mod.compute_score(
        REPO_ROOT,
        "examples/observability/sample-operational-snapshot.json",
        "docs/observability/observability-manifest.json",
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["risk_level"] in ("low", "medium")
    for k in (
        "health_score",
        "readiness_score",
        "evidence_score",
        "diagnostics_score",
        "runtime_health_score",
    ):
        assert isinstance(payload[k], int)
        assert 0 <= payload[k] <= 100
    assert "findings" in payload
    assert isinstance(payload["findings"], list)
    raw = ohs_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_score_low_when_pristine(ohs_mod, tmp_path: Path):
    (tmp_path / "snap.json").write_text(json.dumps(_good_snapshot()), encoding="utf-8")
    payload, code = ohs_mod.compute_score(tmp_path, "snap.json", "missing-manifest.json")
    assert code == 0
    assert payload["risk_level"] == "low"
    assert payload["health_score"] >= 95
    assert payload["readiness_score"] == 100


def test_score_critical_when_invalid_snapshot(ohs_mod, tmp_path: Path):
    (tmp_path / "snap.json").write_text("{}", encoding="utf-8")
    payload, code = ohs_mod.compute_score(tmp_path, "snap.json", "missing-manifest.json")
    assert code == 1
    assert payload["risk_level"] == "critical"
    assert payload["ok"] is False


def test_score_high_when_readiness_false(ohs_mod, tmp_path: Path):
    snap = _good_snapshot()
    snap["readiness"]["migration_state_consistent"] = False
    (tmp_path / "snap.json").write_text(json.dumps(snap), encoding="utf-8")
    payload, code = ohs_mod.compute_score(tmp_path, "snap.json", "missing-manifest.json")
    assert code == 1
    assert payload["ok"] is False
    assert payload["risk_level"] in ("medium", "high", "critical")
    assert any("migration_state_consistent_false" in f for f in payload["findings"])
