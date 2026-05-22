"""Tests for scripts/validate_extension_package.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_extension_package.py"
    spec = importlib.util.spec_from_file_location("validate_extension_package", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vep_mod():
    return _load_mod()


def test_validate_sample_package(vep_mod):
    payload, code = vep_mod.validate_extension_package(
        REPO_ROOT,
        "examples/marketplace/sample-extension-package.json",
        "docs/marketplace/marketplace-manifest.json",
    )
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    raw = vep_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_validate_bad_name(vep_mod, tmp_path: Path):
    man = tmp_path / "marketplace-manifest.json"
    man.write_text(
        json.dumps(
            {
                "extension_types": [
                    {
                        "id": "policy_module",
                        "name": "P",
                        "summary": "Summary text long enough for validation rules here.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "art.txt").write_text("artifact bytes for path validation.", encoding="utf-8")
    pkg = tmp_path / "bad.json"
    pkg.write_text(
        json.dumps(
            {
                "artifacts": [{"path": "art.txt"}],
                "compatibility": {"k": "v"},
                "extension_type": "policy_module",
                "name": "Invalid_Name",
                "permissions": ["p"],
                "publisher": {"id": "x"},
                "review_status": "draft",
                "version": "1.0.0",
            }
        ),
        encoding="utf-8",
    )
    payload, code = vep_mod.validate_extension_package(tmp_path, "bad.json", "marketplace-manifest.json")
    assert code == 1
    assert "name_invalid_format" in payload["errors"]


def test_subprocess_json_roundtrip():
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "validate_extension_package.py"),
            "--json",
            "--repo-root",
            str(REPO_ROOT),
            "--package",
            "examples/marketplace/sample-extension-package.json",
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
