"""Tests for scripts/validate_customer_operations_manifest.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_customer_operations_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_customer_operations_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vcom_mod():
    return _load_mod()


def test_validate_real_manifest(vcom_mod):
    payload, code = vcom_mod.validate_manifest(REPO_ROOT, "docs/operations/customer-operations-manifest.json")
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    assert payload["failures"] == []
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = vcom_mod.dumps_json(payload)
    assert json.loads(raw) == payload
    assert list(json.loads(raw).keys()) == sorted(json.loads(raw).keys())


def test_validate_missing_manifest(vcom_mod, tmp_path: Path):
    payload, code = vcom_mod.validate_manifest(tmp_path, "docs/operations/customer-operations-manifest.json")
    assert code == 1
    assert payload["ok"] is False
    assert payload["errors"]


def test_validate_missing_required_field(vcom_mod, tmp_path: Path):
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps({"production_onboarding": {"summary": "x" * 30}}), encoding="utf-8")
    payload, code = vcom_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert payload["ok"] is False
    assert any("missing_required_key" in e for e in payload["errors"])


def test_validate_missing_referenced_doc(vcom_mod, tmp_path: Path):
    doc = {
        "customer_success": {"summary": "Enough text here for customer success summary."},
        "deployment_readiness": {"summary": "Enough text here for deployment readiness summary."},
        "incident_response": {"summary": "Enough text here for incident response summary."},
        "non_goals": ["a"],
        "production_onboarding": {"summary": "Enough text here for production onboarding summary."},
        "referenced_documents": [{"path": "missing-doc-ops.md", "role": "r"}],
        "referenced_examples": [{"path": "missing-ex.md", "role": "e"}],
        "renewal_readiness": {"summary": "Enough text here for renewal readiness summary."},
        "required_checks": ["check-one"],
        "support_model": {"summary": "Enough text here for support model summary."},
    }
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps(doc), encoding="utf-8")
    payload, code = vcom_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert payload["ok"] is False
    assert any("referenced_document_missing" in e or "referenced_example_missing" in e for e in payload["errors"])


def test_subprocess_json_roundtrip(vcom_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "validate_customer_operations_manifest.py"),
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
