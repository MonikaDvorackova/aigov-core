"""Tests for scripts/revenue_intelligence_check.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "revenue_intelligence_check.py"
    spec = importlib.util.spec_from_file_location("revenue_intelligence_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ri_mod():
    return _load_mod()


def test_compute_revenue_intelligence_real_repo_stable_shape(ri_mod):
    payload, code = ri_mod.compute_revenue_intelligence(REPO_ROOT)
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
        "ok",
        "score",
        "version",
        "warnings",
    }
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = ri_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_compute_revenue_intelligence_missing_paths(ri_mod, tmp_path: Path):
    payload, code = ri_mod.compute_revenue_intelligence(tmp_path)
    assert code == 1
    assert payload["ok"] is False
    assert len(payload["failures"]) > 0


def test_subprocess_json_roundtrip_real_repo(ri_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "revenue_intelligence_check.py"),
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
