"""Tests for scripts/validate_governance_control_snapshot.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_governance_control_snapshot.py"
    spec = importlib.util.spec_from_file_location("validate_governance_control_snapshot", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vgs_mod():
    return _load_mod()


def test_validate_real_sample(vgs_mod):
    payload, code = vgs_mod.validate_sample(REPO_ROOT, "examples/policy-intelligence/sample-governance-control-snapshot.json")
    assert code == 0
    assert payload["ok"] is True
    assert payload["failures"] == []
    raw = vgs_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_schema_errors_empty(vgs_mod):
    assert vgs_mod.schema_errors({}) != []


def test_subprocess_json_roundtrip(vgs_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "validate_governance_control_snapshot.py"),
            "--json",
            "--repo-root",
            str(REPO_ROOT),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["ok"] is True


def test_reviewed_exceeds_registered(vgs_mod):
    bad = {
        "controls": [
            {
                "control_id": "c1",
                "evidence_attached": True,
                "gap_severity": "none",
                "maturity_level": 2,
            }
        ],
        "governance_process": {
            "exception_process_documented": True,
            "quarterly_reviews_done_last_year": 2,
            "segregation_of_duties": True,
        },
        "org_id": "o",
        "policy_inventory": {
            "enforced_in_ci_count": 0,
            "registered_policies_count": 1,
            "reviewed_policies_count": 5,
        },
        "snapshot_version": "1",
    }
    assert "policy_inventory.reviewed_exceeds_registered" in vgs_mod.schema_errors(bad)
