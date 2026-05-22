"""Tests for scripts/validate_developer_integrations_manifest.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_developer_integrations_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_developer_integrations_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vm_mod():
    return _load_mod()


def test_validate_real_manifest_ok(vm_mod):
    payload, code = vm_mod.validate_manifest(REPO_ROOT, "docs/integrations/developer-integrations-manifest.json")
    assert code == 0
    assert payload["ok"] is True
    assert payload["failures"] == []
    raw = vm_mod.dumps_json(payload)
    parsed = json.loads(raw)
    assert parsed == payload
    assert list(parsed.keys()) == sorted(parsed.keys())


def test_missing_required_field(vm_mod, tmp_path: Path):
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({"integration_program": {"summary": "x" * 30}}), encoding="utf-8")
    payload, code = vm_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert payload["ok"] is False
    assert any("missing_required_key" in e for e in payload["failures"])


def test_missing_referenced_document(vm_mod, tmp_path: Path):
    data = {
        "integration_program": {"summary": "x" * 30},
        "supported_integrations": [{"id": "a", "summary": "y" * 30}],
        "automation_packs": [{"id": "p", "path": "examples/integrations/sample-automation-pack.json", "summary": "z" * 30}],
        "developer_workflows": ["one workflow step is long enough here yes"],
        "authentication_model": {"summary": "auth model summary text goes here ok"},
        "ci_cd_model": {"summary": "ci cd model summary text goes here ok"},
        "local_tooling": {"summary": "local tooling summary text goes here ok"},
        "referenced_documents": [{"path": "no/such/file.md", "title": "t"}],
        "referenced_examples": [{"path": "examples/integrations/README.md", "title": "e"}],
        "required_checks": ["make gate"],
        "non_goals": ["not a goal string is long enough here"],
    }
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "examples" / "integrations").mkdir(parents=True)
    sp = Path(__file__).resolve().parents[2] / "examples" / "integrations" / "sample-automation-pack.json"
    (tmp_path / "examples" / "integrations" / "sample-automation-pack.json").write_text(
        sp.read_text(encoding="utf-8"), encoding="utf-8"
    )
    ex = Path(__file__).resolve().parents[2] / "examples" / "integrations" / "README.md"
    (tmp_path / "examples" / "integrations" / "README.md").write_text(ex.read_text(encoding="utf-8"), encoding="utf-8")

    payload, code = vm_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert any("referenced_document_missing" in e for e in payload["failures"])


def test_subprocess_json_roundtrip(vm_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "validate_developer_integrations_manifest.py"),
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
