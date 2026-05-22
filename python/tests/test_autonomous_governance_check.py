"""Tests for scripts/autonomous_governance_check.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "autonomous_governance_check.py"
    spec = importlib.util.spec_from_file_location("autonomous_governance_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def agc_mod():
    return _load_mod()


def test_run_check_real_repo_default(agc_mod):
    payload, code = agc_mod.run_check(
        REPO_ROOT,
        "autonomous/autonomous-governance-manifest.json",
        multi_agent=False,
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert payload["multi_agent"] is False
    names = sorted(c["name"] for c in payload["checks"])
    assert names == sorted(
        [
            "autonomous_json_bundle",
            "documentation_paths",
            "example_drivers",
            "makefile_wiring",
            "multi_agent_coordination",
        ]
    )
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    assert payload["checks"] == sorted(payload["checks"], key=lambda c: c["name"])
    assert not payload["failures"]


def test_run_check_real_repo_multi_agent(agc_mod):
    payload, code = agc_mod.run_check(
        REPO_ROOT,
        "autonomous/autonomous-governance-manifest.json",
        multi_agent=True,
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert payload["multi_agent"] is True
    assert not payload["failures"]
