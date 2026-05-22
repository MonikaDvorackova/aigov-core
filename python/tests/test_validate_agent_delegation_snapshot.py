"""Tests for scripts/validate_agent_delegation_snapshot.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_agent_delegation_snapshot.py"
    spec = importlib.util.spec_from_file_location("validate_agent_delegation_snapshot", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vds_mod():
    return _load_mod()


def _good_snapshot() -> dict:
    return {
        "approval_chain": {
            "human_in_loop_observed": True,
            "human_in_loop_required": False,
            "recorded_approvals": 1,
            "required_approvals": 1,
            "stale_pending_approvals": 0,
        },
        "auditability": {
            "correlation_ids_present_rate_percent": 100,
            "decision_artifacts_exported": True,
            "delegation_edges_logged": True,
            "retention_policy_acknowledged": True,
        },
        "captured_at": "2026-05-12T12:00:00Z",
        "delegation": {
            "cross_tenant_delegation_observed": False,
            "delegate_agent_ids": ["w1"],
            "delegation_scopes": ["read"],
            "delegator_agent_id": "orch",
            "max_delegation_depth_observed": 1,
        },
        "environment": "staging",
        "override_governance": {
            "emergency_break_glass_used": False,
            "override_events_observed": 0,
            "undocumented_override_events": 0,
        },
        "schema_version": 1,
        "snapshot_id": "snap_ok",
    }


def test_validate_real_snapshot(vds_mod):
    rel = "examples/agent-governance/sample-agent-delegation-snapshot.json"
    payload, code = vds_mod.validate_snapshot(REPO_ROOT, rel)
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    raw = vds_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_validate_missing_snapshot(vds_mod, tmp_path: Path):
    payload, code = vds_mod.validate_snapshot(tmp_path, "missing.json")
    assert code == 1
    assert payload["ok"] is False


def test_validate_cross_tenant_invalid_type(vds_mod, tmp_path: Path):
    snap = _good_snapshot()
    snap["delegation"]["cross_tenant_delegation_observed"] = "no"
    (tmp_path / "s.json").write_text(json.dumps(snap), encoding="utf-8")
    payload, code = vds_mod.validate_snapshot(tmp_path, "s.json")
    assert code == 1
    assert any("cross_tenant_invalid" in e for e in payload["errors"])
