"""Tests for scripts/validate_control_plane_manifest.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_control_plane_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_control_plane_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vcp_mod():
    return _load_mod()


def test_validate_real_manifest(vcp_mod):
    payload, code = vcp_mod.validate_manifest(REPO_ROOT, "docs/control-plane/control-plane-manifest.json")
    assert code == 0
    assert payload["ok"] is True
    assert payload["failures"] == []
    raw = vcp_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_domain_weights_sum_100_enforced(vcp_mod, tmp_path: Path):
    bad_manifest = {
        "aggregation_model": {"inputs": list(vcp_mod.DOMAIN_SET), "method": "x", "summary": "ok"},
        "control_plane_program": "p",
        "escalation_model": {"method": "x", "summary": "ok"},
        "governance_posture_levels": [{"description": "d", "level": "BLOCKED", "min_score": 0}],
        "non_goals": ["n"],
        "referenced_documents": [{"path": "docs/index.md"}],
        "referenced_examples": [{"path": "examples/control-plane/sample-governance-posture-snapshot.json"}],
        "required_checks": ["make gate"],
        "scoring_model": {
            "domain_weights": {d: 1 for d in vcp_mod.DOMAIN_SET},
            "method": "x",
            "penalty_by_severity": {s: 1 for s in vcp_mod.SEVERITIES},
            "status_model": {"fail_penalty_multiplier": 1.0, "unknown_penalty_multiplier": 0.4},
            "summary": "ok",
        },
        "signal_domains": [{"domain": d, "summary": "x"} for d in sorted(vcp_mod.DOMAIN_SET)],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(bad_manifest), encoding="utf-8")
    payload, code = vcp_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert payload["ok"] is False
    assert any("domain_weights_sum_not_100" in e for e in payload["errors"])

