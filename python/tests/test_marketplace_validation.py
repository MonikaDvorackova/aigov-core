"""Tests for policy pack marketplace validators (Phase 14)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_validate_pack():
    path = REPO_ROOT / "scripts" / "validate_policy_pack.py"
    spec = importlib.util.spec_from_file_location("validate_policy_pack", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_validate_manifest():
    path = REPO_ROOT / "scripts" / "validate_marketplace_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_marketplace_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vpp_mod():
    return _load_validate_pack()


@pytest.fixture(scope="module")
def vmm_mod():
    return _load_validate_manifest()


def _valid_policy_module() -> dict:
    return {
        "schema_version": "govai.standards.governance_policy_module.v1",
        "policy": {"id": "pol.test", "name": "Test", "version": "1.0.0"},
        "requirements": [{"code": "c1", "required_evidence": ["ev.a"]}],
    }


def _write_pack(repo: Path, pack_name: str, manifest: dict) -> None:
    pdir = repo / pack_name
    pdir.mkdir(parents=True)
    mod_path = manifest["policy_module_path"]
    (pdir / mod_path).write_text(json.dumps(_valid_policy_module()), encoding="utf-8")
    (pdir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_validate_pack_example_ok(vpp_mod):
    payload, code = vpp_mod.validate_pack(REPO_ROOT, "examples/marketplace/eu-ai-act-basic")
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]


def test_validate_pack_missing_required_field(vpp_mod, tmp_path: Path):
    manifest = {
        "artifact_type": "govai.policy_pack.policy_module",
        "compatibility": {"govai_policy_module_interchange": "govai.standards.governance_policy_module.v1"},
        "description": "x" * 30,
        "id": "missing-license-pack",
        "maintainers": ["a@b.invalid"],
        "name": "n",
        "policy_module_path": "policy-module.json",
        "schema_version": "1",
        "tags": ["t"],
        "version": "1.0.0",
    }
    _write_pack(tmp_path, "missing-license-pack", manifest)
    payload, code = vpp_mod.validate_pack(tmp_path, "missing-license-pack")
    assert code == 1
    assert payload["ok"] is False
    assert any("missing_required_field:license" in e for e in payload["errors"])


def test_validate_pack_unsupported_schema_version(vpp_mod, tmp_path: Path):
    manifest = {
        "artifact_type": "govai.policy_pack.policy_module",
        "compatibility": {"govai_policy_module_interchange": "govai.standards.governance_policy_module.v1"},
        "description": "x" * 30,
        "id": "bad-schema",
        "license": "MIT",
        "maintainers": ["a@b.invalid"],
        "name": "n",
        "policy_module_path": "policy-module.json",
        "schema_version": "99",
        "tags": ["t"],
        "version": "1.0.0",
    }
    _write_pack(tmp_path, "bad-schema", manifest)
    payload, code = vpp_mod.validate_pack(tmp_path, "bad-schema")
    assert code == 1
    assert any("unsupported_schema_version" in e for e in payload["errors"])


def test_catalog_manifest_mismatch(vmm_mod, tmp_path: Path):
    (tmp_path / "marketplace").mkdir()
    pack_name = "p1"
    manifest = {
        "artifact_type": "govai.policy_pack.policy_module",
        "compatibility": {"govai_policy_module_interchange": "govai.standards.governance_policy_module.v1"},
        "description": "x" * 30,
        "id": "actual-id",
        "license": "MIT",
        "maintainers": ["a@b.invalid"],
        "name": "n",
        "policy_module_path": "policy-module.json",
        "schema_version": "1",
        "tags": ["t"],
        "version": "1.0.0",
    }
    _write_pack(tmp_path, pack_name, manifest)
    catalog = {
        "catalog_kind": "govai_policy_pack_marketplace",
        "policy_packs": [{"id": "catalog-id", "path": pack_name}],
        "schema_version": "1",
        "summary": "x" * 30,
    }
    (tmp_path / "marketplace" / "manifest.json").write_text(json.dumps(catalog), encoding="utf-8")
    payload, code = vmm_mod.validate_manifest(tmp_path, "marketplace/manifest.json")
    assert code == 1
    assert any("pack_manifest_id_mismatch" in e for e in payload["errors"])


def test_catalog_duplicate_pack_id(vmm_mod, tmp_path: Path):
    (tmp_path / "marketplace").mkdir()
    manifest = {
        "artifact_type": "govai.policy_pack.policy_module",
        "compatibility": {"govai_policy_module_interchange": "govai.standards.governance_policy_module.v1"},
        "description": "x" * 30,
        "id": "dup",
        "license": "MIT",
        "maintainers": ["a@b.invalid"],
        "name": "n",
        "policy_module_path": "policy-module.json",
        "schema_version": "1",
        "tags": ["t"],
        "version": "1.0.0",
    }
    _write_pack(tmp_path, "a1", manifest)
    _write_pack(tmp_path, "a2", {**manifest, "id": "dup"})
    catalog = {
        "catalog_kind": "govai_policy_pack_marketplace",
        "policy_packs": [
            {"id": "dup", "path": "a1"},
            {"id": "dup", "path": "a2"},
        ],
        "schema_version": "1",
        "summary": "x" * 30,
    }
    (tmp_path / "marketplace" / "manifest.json").write_text(json.dumps(catalog), encoding="utf-8")
    payload, code = vmm_mod.validate_manifest(tmp_path, "marketplace/manifest.json")
    assert code == 1
    assert any(e.startswith("duplicate_pack_id:") for e in payload["errors"])


def test_catalog_unsupported_schema_version(vmm_mod, tmp_path: Path):
    (tmp_path / "marketplace").mkdir()
    catalog = {
        "catalog_kind": "govai_policy_pack_marketplace",
        "policy_packs": [],
        "schema_version": "99",
        "summary": "x" * 30,
    }
    (tmp_path / "marketplace" / "manifest.json").write_text(json.dumps(catalog), encoding="utf-8")
    payload, code = vmm_mod.validate_manifest(tmp_path, "marketplace/manifest.json")
    assert code == 1
    assert any("unsupported_catalog_schema_version" in e for e in payload["errors"])


def test_real_policy_catalog_manifest(vmm_mod):
    payload, code = vmm_mod.validate_manifest(REPO_ROOT, "marketplace/manifest.json")
    assert code == 0
    assert payload["ok"] is True


def test_subprocess_validate_catalog_positional():
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "validate_marketplace_manifest.py"),
            "--json",
            "--repo-root",
            str(REPO_ROOT),
            "marketplace/manifest.json",
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
