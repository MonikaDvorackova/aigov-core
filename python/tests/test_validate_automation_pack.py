"""Tests for scripts/validate_automation_pack.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PACK = "examples/integrations/sample-automation-pack.json"


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_automation_pack.py"
    spec = importlib.util.spec_from_file_location("validate_automation_pack", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ap_mod():
    return _load_mod()


def test_validate_sample_pack_ok(ap_mod):
    payload, code = ap_mod.validate_pack(REPO_ROOT, SAMPLE_PACK)
    assert code == 0
    assert payload["ok"] is True
    raw = ap_mod.dumps_json(payload)
    parsed = json.loads(raw)
    assert list(parsed.keys()) == sorted(parsed.keys())


def test_invalid_command_argv(ap_mod, tmp_path: Path):
    bad = {
        "schema_version": "1",
        "pack_id": "x",
        "name": "n",
        "summary": "summary text long enough",
        "commands": [{"id": "c1", "argv": ["ok", ""], "description": "d"}],
        "artifacts": [{"path": "README.md", "kind": "k", "description": "artifact desc is long ok"}],
    }
    # README.md at repo root may not exist in tmp_path - use a file we create
    p = tmp_path / "pack.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    (tmp_path / "README.md").write_text("x" * 80, encoding="utf-8")
    payload, code = ap_mod.validate_pack(tmp_path, "pack.json")
    assert code == 1
    assert any("commands_argv_empty_segment" in e for e in payload["failures"])


def test_invalid_artifact_missing(ap_mod, tmp_path: Path):
    bad = {
        "schema_version": "1",
        "pack_id": "x",
        "name": "n",
        "summary": "summary text long enough",
        "commands": [{"id": "c1", "argv": ["true"], "description": "desc ok long enough here"}],
        "artifacts": [{"path": "missing-artifact.txt", "kind": "k", "description": "artifact desc is long ok"}],
    }
    p = tmp_path / "pack.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    payload, code = ap_mod.validate_pack(tmp_path, "pack.json")
    assert code == 1
    assert any("artifact_missing" in e for e in payload["failures"])


def test_subprocess_validate_pack(ap_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "validate_automation_pack.py"),
            "--json",
            "--repo-root",
            str(REPO_ROOT),
            "--pack",
            SAMPLE_PACK,
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["ok"] is True
