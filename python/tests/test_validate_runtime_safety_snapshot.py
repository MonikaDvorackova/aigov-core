"""Tests for scripts/validate_runtime_safety_snapshot.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_runtime_safety_snapshot.py"
    spec = importlib.util.spec_from_file_location("validate_runtime_safety_snapshot", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def smod():
    return _load_mod()


def test_validate_sample_snapshot(smod):
    payload, code = smod.validate_snapshot(
        REPO_ROOT,
        "examples/runtime-safety/sample-runtime-safety-snapshot.json",
    )
    assert code == 0
    assert payload["ok"] is True


def test_validate_invalid_snapshot(smod, tmp_path: Path):
    (tmp_path / "bad.json").write_text("{}", encoding="utf-8")
    payload, code = smod.validate_snapshot(tmp_path, "bad.json")
    assert code == 1
    assert payload["ok"] is False
    assert any("missing_required_key" in e for e in payload["errors"])


def test_failure_count_mismatch(smod, tmp_path: Path):
    snap = {
        "captured_at": "2026-05-12T16:00:00Z",
        "diagnostics": {
            "checks": [{"detail": "x", "name": "a", "ok": True}],
            "failure_count": 3,
            "summary": "Summary text long enough for validation rules here.",
            "warning_count": 0,
        },
        "environment": "staging",
        "escalation": {
            "high_risk_sessions_escalated": 0,
            "median_queue_wait_minutes": 0,
            "pending_human_review_count": 0,
            "sla_breaches_observed": 0,
        },
        "guardrails": {
            "content_filter_interventions": 0,
            "guardrail_latency_p95_ms": 0,
            "policy_denies_without_override": 0,
            "prompt_injection_blocks_observed": 0,
            "tool_allowlist_violations_blocked": 0,
        },
        "human_oversight": {
            "active_supervisors_count": 2,
            "attribution_chain_complete_percent": 100,
            "dual_control_sessions_completed": 0,
            "human_review_coverage_percent": 100,
        },
        "override_readiness": {
            "audit_trail_export_latency_p95_seconds": 1,
            "emergency_break_glass_last_drill_days_ago": 1,
            "override_playbook_version_present": True,
            "rollback_procedure_documented": True,
        },
        "schema_version": 1,
        "snapshot_id": "x",
        "window_minutes": 1,
    }
    (tmp_path / "snap.json").write_text(json.dumps(snap), encoding="utf-8")
    payload, code = smod.validate_snapshot(tmp_path, "snap.json")
    assert code == 1
    assert any("failure_count_mismatch" in e for e in payload["errors"])
