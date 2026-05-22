"""Tests for scripts/pilot_execution_check.py JSON and compute_pilot_execution."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "pilot_execution_check.py"
    spec = importlib.util.spec_from_file_location("pilot_execution_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pe_mod():
    return _load_mod()


def test_compute_pilot_execution_real_repo_stable_shape(pe_mod):
    payload, code = pe_mod.compute_pilot_execution(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert payload["version"] == 1
    assert payload["failures"] == []
    assert payload["warnings"] == []
    assert set(payload.keys()) == {
        "checked_paths",
        "checks",
        "failures",
        "min_bytes_threshold",
        "ok",
        "score",
        "version",
        "warnings",
    }
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    for c in payload["checks"]:
        assert "category" in c and "check_id" in c and "ok" in c
    raw = pe_mod.dumps_json(payload)
    parsed = json.loads(raw)
    assert parsed == payload
    assert list(parsed.keys()) == sorted(parsed.keys())


def test_compute_pilot_execution_missing_paths(pe_mod, tmp_path: Path):
    payload, code = pe_mod.compute_pilot_execution(tmp_path)
    assert code == 1
    assert payload["ok"] is False
    assert len(payload["failures"]) > 0
    assert isinstance(payload["checked_paths"], list)


def test_subprocess_json_roundtrip_real_repo(pe_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "pilot_execution_check.py"),
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
