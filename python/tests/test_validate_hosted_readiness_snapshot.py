"""Tests for scripts/validate_hosted_readiness_snapshot.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_hosted_readiness_snapshot.py"
    spec = importlib.util.spec_from_file_location("validate_hosted_readiness_snapshot", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def snap_mod():
    return _load_mod()


def test_validate_snapshot_real_repo(snap_mod):
    payload, code = snap_mod.validate_snapshot(
        REPO_ROOT,
        "examples/hosted-platform/sample-hosted-readiness-snapshot.json",
    )
    assert code == 0
    assert payload["ok"] is True
    assert not payload["failures"]


def test_validate_snapshot_invalid_deployment_bool(snap_mod, tmp_path: Path):
    bad = {
        "captured_at": "2026-05-13T10:00:00Z",
        "deployment": {"ci_gate_green": "not-a-bool"},
        "diagnostics": {
            "checks": [],
            "failure_count": 0,
            "summary": "x" * 30,
            "warning_count": 0,
        },
        "environment": "test",
        "operations": {},
        "schema_version": 1,
        "snapshot_id": "bad",
        "support": {},
        "tenant_onboarding": {},
        "window_minutes": 1,
    }
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    rel = str(p.relative_to(tmp_path))
    payload, code = snap_mod.validate_snapshot(tmp_path, rel)
    assert code == 1
    assert payload["ok"] is False
