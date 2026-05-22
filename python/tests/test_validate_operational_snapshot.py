"""Tests for scripts/validate_operational_snapshot.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_operational_snapshot.py"
    spec = importlib.util.spec_from_file_location("validate_operational_snapshot", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vos_mod():
    return _load_mod()


def _good_snapshot() -> dict:
    return {
        "captured_at": "2026-05-12T15:30:00Z",
        "diagnostics": {
            "checks": [
                {"detail": "ok", "name": "x", "ok": True},
            ],
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
            "audit_service_uptime_minutes": 720,
            "error_rate_percent": 0,
            "open_incidents_count": 0,
        },
        "schema_version": 1,
        "snapshot_id": "snap1",
        "window_minutes": 60,
    }


def test_validate_real_snapshot(vos_mod):
    rel = "examples/observability/sample-operational-snapshot.json"
    payload, code = vos_mod.validate_snapshot(REPO_ROOT, rel)
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    raw = vos_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_validate_missing_snapshot(vos_mod, tmp_path: Path):
    payload, code = vos_mod.validate_snapshot(tmp_path, "missing.json")
    assert code == 1
    assert payload["ok"] is False


def test_validate_failure_count_mismatch(vos_mod, tmp_path: Path):
    snap = _good_snapshot()
    snap["diagnostics"]["checks"].append({"detail": "broke", "name": "y", "ok": False})
    (tmp_path / "s.json").write_text(json.dumps(snap), encoding="utf-8")
    payload, code = vos_mod.validate_snapshot(tmp_path, "s.json")
    assert code == 1
    assert any("diagnostics_failure_count_mismatch" in e for e in payload["errors"])


def test_validate_invalid_error_rate(vos_mod, tmp_path: Path):
    snap = _good_snapshot()
    snap["runtime_health"]["error_rate_percent"] = 150
    (tmp_path / "s.json").write_text(json.dumps(snap), encoding="utf-8")
    payload, code = vos_mod.validate_snapshot(tmp_path, "s.json")
    assert code == 1
    assert any("runtime_health_error_rate_percent_invalid" in e for e in payload["errors"])


def test_validate_readiness_bool_required(vos_mod, tmp_path: Path):
    snap = _good_snapshot()
    snap["readiness"]["audit_ready_endpoint_status"] = "yes"
    (tmp_path / "s.json").write_text(json.dumps(snap), encoding="utf-8")
    payload, code = vos_mod.validate_snapshot(tmp_path, "s.json")
    assert code == 1
    assert any("readiness_audit_ready_endpoint_status_invalid" in e for e in payload["errors"])
