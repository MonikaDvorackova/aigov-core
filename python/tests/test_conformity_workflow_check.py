"""Tests for scripts/conformity_workflow_check.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "conformity_workflow_check.py"
    spec = importlib.util.spec_from_file_location("conformity_workflow_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def cw_mod():
    return _load_mod()


def test_run_check_real_repo_full(cw_mod):
    payload, code = cw_mod.run_check(
        REPO_ROOT,
        "conformity/regulatory-workflow-manifest.json",
        regulatory_workflow_only=False,
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert payload["regulatory_workflow_only"] is False
    names = sorted(c["name"] for c in payload["checks"])
    assert names == sorted(
        [
            "ai_act_control_mapping",
            "conformity_assessment_workflow",
            "documentation_paths",
            "example_drivers",
            "incident_reporting_workflow",
            "makefile_wiring",
            "post_market_monitoring_workflow",
            "regulatory_references",
            "regulatory_workflow_manifest",
            "risk_management_workflow",
            "sample_conformity_assessment_snapshot",
            "technical_documentation_workflow",
        ]
    )
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    assert payload["checks"] == sorted(payload["checks"], key=lambda c: c["name"])
    assert not payload["failures"]


def test_run_check_regulatory_workflow_only(cw_mod):
    payload, code = cw_mod.run_check(
        REPO_ROOT,
        "conformity/regulatory-workflow-manifest.json",
        regulatory_workflow_only=True,
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["regulatory_workflow_only"] is True
    names = sorted(c["name"] for c in payload["checks"])
    assert names == sorted(
        [
            "ai_act_control_mapping",
            "conformity_assessment_workflow",
            "makefile_wiring",
            "regulatory_workflow_manifest",
        ]
    )
    assert not payload["failures"]


def test_run_check_missing_repo_root_paths(cw_mod, tmp_path: Path):
    payload, code = cw_mod.run_check(
        tmp_path,
        "conformity/regulatory-workflow-manifest.json",
        regulatory_workflow_only=False,
    )
    assert code == 1
    assert payload["ok"] is False
