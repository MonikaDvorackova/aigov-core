"""Tests for scripts/validate_customer_analytics_manifest.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_customer_analytics_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_customer_analytics_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def van_mod():
    return _load_mod()


def test_validate_real_manifest(van_mod):
    payload, code = van_mod.validate_manifest(REPO_ROOT, "docs/analytics/customer-analytics-manifest.json")
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    assert payload["failures"] == []
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = van_mod.dumps_json(payload)
    assert json.loads(raw) == payload
    assert list(json.loads(raw).keys()) == sorted(json.loads(raw).keys())


def test_validate_missing_manifest(van_mod, tmp_path: Path):
    payload, code = van_mod.validate_manifest(tmp_path, "docs/analytics/customer-analytics-manifest.json")
    assert code == 1
    assert payload["ok"] is False
    assert payload["errors"]


def test_validate_missing_required_key(van_mod, tmp_path: Path):
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps({"analytics_program": {"summary": "x" * 30}}), encoding="utf-8")
    payload, code = van_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert payload["ok"] is False
    assert any("missing_required_key" in e for e in payload["errors"])


def test_validate_missing_referenced_path(van_mod, tmp_path: Path):
    chk = tmp_path / "dummy_check.txt"
    chk.write_text("#" * 80, encoding="utf-8")
    doc = {
        "adoption_signals": {"summary": "Enough text here for adoption signals summary."},
        "analytics_program": {"summary": "Enough text here for analytics program summary."},
        "data_boundaries": {"summary": "Enough text here for data boundaries summary."},
        "executive_review": {"summary": "Enough text here for executive review summary."},
        "expansion_intelligence": {"summary": "Enough text here for expansion intelligence summary."},
        "health_model": {"summary": "Enough text here for health model summary."},
        "non_goals": ["not a legal certification statement here"],
        "referenced_documents": [{"path": "missing-analytics-doc.md", "role": "r"}],
        "referenced_examples": [],
        "renewal_risk": {"summary": "Enough text here for renewal risk summary."},
        "required_checks": ["dummy_check.txt"],
    }
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps(doc), encoding="utf-8")
    payload, code = van_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert payload["ok"] is False
    assert any("referenced_path_missing" in e for e in payload["errors"])


def test_subprocess_json_roundtrip(van_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "validate_customer_analytics_manifest.py"),
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
