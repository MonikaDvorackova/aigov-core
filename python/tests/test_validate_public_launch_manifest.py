"""Tests for scripts/validate_public_launch_manifest.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_public_launch_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_public_launch_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_mod()


def test_validate_real_manifest(mod):
    payload, code = mod.validate_manifest(REPO_ROOT, "docs/launch/public-launch-manifest.json")
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    raw = mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_validate_missing_manifest(mod, tmp_path: Path):
    payload, code = mod.validate_manifest(tmp_path, "docs/launch/public-launch-manifest.json")
    assert code == 1
    assert payload["ok"] is False


def test_validate_bad_schema_version(mod, tmp_path: Path):
    m = tmp_path / "m.json"
    m.write_text(
        json.dumps(
            {
                "certification_status": "x" * 20,
                "documentation_anchors": ["README.md"],
                "ecosystem_packages": ["README.md"],
                "issued_at": "2026-05-13T00:00:00Z",
                "launch_id": "l",
                "product_version": "1.0.0",
                "readiness_flags": {
                    "ci_public_launch_artifacts": True,
                    "make_public_launch_targets": True,
                    "sample_snapshot_committed": True,
                    "stdlib_validators_shipped": True,
                },
                "schema_version": 0,
                "standardization_readiness_snapshot": "README.md",
                "target_channels": ["oss"],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("x", encoding="utf-8")
    payload, code = mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert any("schema_version" in e for e in payload["errors"])


def test_subprocess_json_roundtrip(mod):
    import subprocess

    r = subprocess.run(
        ["python3", str(REPO_ROOT / "scripts" / "validate_public_launch_manifest.py"), "--json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["ok"] is True
