"""Tests for scripts/commercial_readiness_check.py JSON and compute_commercial_readiness."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "commercial_readiness_check.py"
    spec = importlib.util.spec_from_file_location("commercial_readiness_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def cr_mod():
    return _load_mod()


def test_compute_commercial_readiness_real_repo_stable_shape(cr_mod):
    payload, code = cr_mod.compute_commercial_readiness(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["missing_required"] == []
    assert payload["version"] == 1
    assert set(payload.keys()) == {"categories", "checked_paths", "missing_required", "ok", "version"}
    cats = payload["categories"]
    for _name, c in cats.items():
        assert set(c.keys()) == {"missing", "ok", "paths_checked", "present"}
        assert c["ok"] is True
        assert c["missing"] == []
    raw = cr_mod.dumps_json(payload)
    parsed = json.loads(raw)
    assert parsed == payload
    assert list(parsed.keys()) == sorted(parsed.keys())


def test_compute_commercial_readiness_missing_required(cr_mod, tmp_path: Path):
    payload, code = cr_mod.compute_commercial_readiness(tmp_path)
    assert code == 1
    assert payload["ok"] is False
    assert len(payload["missing_required"]) > 0
    assert all(isinstance(x, str) for x in payload["checked_paths"])


def test_json_stdout_roundtrip_fail_empty_dir(cr_mod, tmp_path: Path):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "commercial_readiness_check.py"),
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
