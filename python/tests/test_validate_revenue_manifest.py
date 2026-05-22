"""Tests for scripts/validate_revenue_manifest.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_revenue_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_revenue_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rm_mod():
    return _load_mod()


def test_validate_real_manifest(rm_mod):
    payload, code = rm_mod.validate_manifest(REPO_ROOT, "docs/revenue/revenue-manifest.json")
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = rm_mod.dumps_json(payload)
    data = json.loads(raw)
    assert data == payload
    assert list(data.keys()) == sorted(data.keys())


def test_missing_required_field(rm_mod, tmp_path: Path):
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps({"version": 1, "description": "x" * 20}), encoding="utf-8")
    payload, code = rm_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert payload["ok"] is False
    assert any("missing_required_key" in e for e in payload["errors"])


def test_missing_referenced_path(rm_mod, tmp_path: Path):
    (tmp_path / "ok-doc.md").write_text("# " + "x" * 80, encoding="utf-8")
    (tmp_path / "ok-ex.md").write_text("# " + "y" * 80, encoding="utf-8")
    doc = {
        "description": "Enough characters in description here.",
        "non_goals": ["no billing changes"],
        "pilot_conversion_criteria": ["c1"],
        "pricing_packages": [{"id": "a", "name": "n", "summary": "s"}],
        "proposal_assets": [{"id": "x", "path": "MISSING.md", "summary": "y"}],
        "qualification_criteria": ["q"],
        "referenced_documents": [{"path": "ok-doc.md", "role": "r"}],
        "referenced_examples": [{"path": "ok-ex.md"}],
        "risk_register_summary": "x" * 40,
        "roi_inputs": {
            "baseline_cost": 1,
            "expected_savings": 2,
            "implementation_cost": 3,
            "payback_months": 4,
        },
        "sales_process": {"stages": ["a"]},
        "version": 1,
    }
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps(doc), encoding="utf-8")
    payload, code = rm_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert any("proposal_asset_path_missing" in e for e in payload["errors"])


def test_subprocess_json_roundtrip(rm_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "validate_revenue_manifest.py"),
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
    assert list(data.keys()) == sorted(data.keys())
