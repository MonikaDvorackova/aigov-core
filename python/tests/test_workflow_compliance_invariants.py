"""Static checks on workflow YAML (text-based; no PyYAML dependency)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_govai_ci_is_portable_without_localhost_audit_orchestration() -> None:
    p = REPO_ROOT / ".github/workflows/govai-ci.yml"
    t = p.read_text(encoding="utf-8")
    assert "aigov-core-portable" in t
    assert "ci_portable_artifact_bundle.py" in t
    assert "verify-evidence-pack --portable-only" in t
    assert "audit_bg" not in t
    assert "8088/ready" not in t
    assert "Wait for audit readiness" not in t


def test_compliance_workflow_does_not_poll_ready_or_start_local_audit() -> None:
    p = REPO_ROOT / ".github/workflows/compliance.yml"
    t = p.read_text(encoding="utf-8")
    assert "expected HTTP 200 from GET /ready" not in t
    assert "8088/ready" not in t
    assert "  govai-compliance-gate:" not in t


def test_govai_smoke_remains_manual_operator_workflow() -> None:
    p = REPO_ROOT / ".github/workflows/govai-smoke.yml"
    t = p.read_text(encoding="utf-8")
    assert "workflow_dispatch" in t
    assert "AIGov Core CI does NOT" in t or "manual" in t.lower()
