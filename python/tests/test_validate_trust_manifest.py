"""Tests for scripts/validate_trust_manifest.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_trust_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_trust_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vm_mod():
    return _load_mod()


def test_validate_real_manifest(vm_mod):
    payload, code = vm_mod.validate_manifest(REPO_ROOT, "docs/trust/trust-manifest.json")
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    assert payload["failures"] == []
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = vm_mod.dumps_json(payload)
    assert json.loads(raw) == payload
    assert list(json.loads(raw).keys()) == sorted(json.loads(raw).keys())


def test_validate_missing_manifest(vm_mod, tmp_path: Path):
    payload, code = vm_mod.validate_manifest(tmp_path, "docs/trust/trust-manifest.json")
    assert code == 1
    assert payload["ok"] is False
    assert payload["errors"]


def test_validate_missing_required_field(vm_mod, tmp_path: Path):
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps({"version": 1}), encoding="utf-8")
    payload, code = vm_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert payload["ok"] is False
    assert any("missing_required_key" in e for e in payload["errors"])


def test_validate_missing_referenced_doc(vm_mod, tmp_path: Path):
    doc = {
        "disclosure_policy_reference": "MISSING_FILE_XXX.md",
        "incident_response_statement": "Enough text here for incident response statement minimum length.",
        "ledger_durability_statement": "Enough text here for ledger durability statement minimum length.",
        "operational_probes": [
            {"command": "c", "description": "d description", "name": "n"},
        ],
        "security_controls": [{"description": "d", "evidence": "also-missing.md", "id": "sc1"}],
        "tenant_isolation_statement": "Enough text here for tenant isolation statement minimum length.",
        "trust_documents": [{"path": "missing-trust-doc.md", "role": "r"}],
        "version": 1,
    }
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps(doc), encoding="utf-8")
    payload, code = vm_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert payload["ok"] is False
    assert any("missing" in e or "trust_document_missing" in e for e in payload["errors"])


def test_subprocess_json_roundtrip(vm_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "validate_trust_manifest.py"),
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
