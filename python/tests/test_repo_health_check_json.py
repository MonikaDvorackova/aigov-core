"""Tests for scripts/repo_health_check.py JSON and compute_health."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "repo_health_check.py"
    spec = importlib.util.spec_from_file_location("repo_health_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rh_mod():
    return _load_mod()


def test_compute_health_real_repo_stable_shape(rh_mod):
    payload, code = rh_mod.compute_health(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["missing_required"] == []
    assert set(payload.keys()) == {
        "checked_paths",
        "missing_optional",
        "missing_required",
        "ok",
        "optional_files_present",
        "required_files_present",
    }
    raw = rh_mod.dumps_json(payload)
    parsed = json.loads(raw)
    assert parsed == payload
    assert list(parsed.keys()) == sorted(parsed.keys())


def test_compute_health_missing_required(rh_mod, tmp_path: Path):
    payload, code = rh_mod.compute_health(tmp_path)
    assert code == 1
    assert payload["ok"] is False
    assert len(payload["missing_required"]) > 0
    assert payload["required_files_present"] == []
    assert all(isinstance(x, str) for x in payload["checked_paths"])


def test_json_stdout_roundtrip(rh_mod, tmp_path: Path):
    """CLI --json on empty dir: deterministic single-line JSON."""
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "repo_health_check.py"),
            "--json",
            "--repo-root",
            str(tmp_path),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 1
    line = r.stdout.strip()
    data = json.loads(line)
    assert data["ok"] is False
    assert list(data.keys()) == sorted(data.keys())
