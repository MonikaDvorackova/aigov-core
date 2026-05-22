"""Tests for scripts/agent_governance_score.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "agent_governance_score.py"
    spec = importlib.util.spec_from_file_location("agent_governance_score", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ags_mod():
    return _load_mod()


def test_score_real_sample(ags_mod):
    payload, code = ags_mod.compute_score(
        REPO_ROOT,
        "examples/agent-governance/sample-agent-delegation-snapshot.json",
        "docs/agent-governance/agent-governance-manifest.json",
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["risk_level"] in ("low", "medium")
    for k in (
        "agent_governance_score",
        "delegation_score",
        "approval_chain_score",
        "override_score",
        "auditability_score",
    ):
        assert isinstance(payload[k], int)
    assert isinstance(payload["findings"], list)
    assert isinstance(payload["recommendations"], list)
    raw = ags_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_score_cross_tenant_fails(ags_mod, tmp_path: Path):
    snap = {
        "approval_chain": {
            "human_in_loop_observed": True,
            "human_in_loop_required": True,
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
            "cross_tenant_delegation_observed": True,
            "delegate_agent_ids": ["w"],
            "delegation_scopes": ["x"],
            "delegator_agent_id": "o",
            "max_delegation_depth_observed": 1,
        },
        "environment": "staging",
        "override_governance": {
            "emergency_break_glass_used": False,
            "override_events_observed": 0,
            "undocumented_override_events": 0,
        },
        "schema_version": 1,
        "snapshot_id": "bad",
    }
    (tmp_path / "s.json").write_text(json.dumps(snap), encoding="utf-8")
    payload, code = ags_mod.compute_score(tmp_path, "s.json", "docs/agent-governance/agent-governance-manifest.json")
    assert code == 1
    assert payload["ok"] is False
