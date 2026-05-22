"""Tests for scripts/agent_governance_check.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "agent_governance_check.py"
    spec = importlib.util.spec_from_file_location("agent_governance_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def agc_mod():
    return _load_mod()


def test_run_check_real_repo(agc_mod):
    payload, code = agc_mod.run_check(
        REPO_ROOT,
        "docs/agent-governance/agent-governance-manifest.json",
        "examples/agent-governance/sample-agent-delegation-snapshot.json",
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    names = sorted(c["name"] for c in payload["checks"])
    assert names == sorted(
        [
            "agent_governance_score",
            "documentation_paths",
            "example_drivers",
            "makefile_wiring",
            "manifest_validation",
            "snapshot_validation",
        ]
    )
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    assert payload["checks"] == sorted(payload["checks"], key=lambda c: c["name"])
    assert not payload["failures"]
