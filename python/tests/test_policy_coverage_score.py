"""Tests for scripts/policy_coverage_score.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "policy_coverage_score.py"
    spec = importlib.util.spec_from_file_location("policy_coverage_score", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pcs_mod():
    return _load_mod()


def test_sample_scores_stable(pcs_mod):
    raw = (REPO_ROOT / "examples/policy-intelligence/sample-governance-control-snapshot.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    payload, code = pcs_mod.compute_scores_from_dict(data)
    assert code == 0
    assert payload["ok"] is True
    assert payload["org_id"] == "org_govai_sample"
    assert payload["policy_coverage_score"] == 64
    assert payload["control_maturity_score"] == 56
    assert payload["gap_risk_score"] == 28
    assert payload["findings"] == [
        "missing_evidence_attachment",
        "review_cadence_below_four_per_year",
        "segregation_of_duties_not_asserted",
    ]
    assert payload["recommendations"] == [
        "attach_audit_or_policy_evidence_for_controls_marked_without_attachment",
        "document_segregation_of_duties_for_sensitive_promotion_paths",
        "increase_ci_policy_enforcement_to_lift_coverage",
        "prioritize_remediation_for_high_and_medium_control_gaps",
        "re_export_scores_after_snapshot_updates",
        "schedule_four_quarterly_policy_governance_reviews_per_year",
    ]
    out = pcs_mod.dumps_json(payload)
    assert list(json.loads(out).keys()) == sorted(json.loads(out).keys())


def test_invalid_payload(pcs_mod):
    payload, code = pcs_mod.compute_scores_from_dict({})
    assert code == 1
    assert payload["ok"] is False


def test_subprocess_sample_input(pcs_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "policy_coverage_score.py"),
            "--input",
            str(REPO_ROOT / "examples/policy-intelligence/sample-governance-control-snapshot.json"),
            "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["policy_coverage_score"] == 64
