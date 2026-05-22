"""Tests for scripts/developer_integrations_check.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "developer_integrations_check.py"
    spec = importlib.util.spec_from_file_location("developer_integrations_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def di_mod():
    return _load_mod()


def test_compute_real_repo_score_100(di_mod):
    payload, code = di_mod.compute_developer_integrations(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert payload["failures"] == []
    assert payload["warnings"] == []
    assert set(payload.keys()) == {"checked_paths", "checks", "failures", "ok", "score", "version", "warnings"}
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = di_mod.dumps_json(payload)
    parsed = json.loads(raw)
    assert parsed == payload
    assert list(parsed.keys()) == sorted(parsed.keys())


def test_compute_empty_repo_fails(di_mod, tmp_path: Path):
    payload, code = di_mod.compute_developer_integrations(tmp_path)
    assert code == 1
    assert payload["ok"] is False
    assert payload["score"] < 100
    assert len(payload["failures"]) > 0


def test_subprocess_json(di_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "developer_integrations_check.py"),
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
    assert data["score"] == 100
    assert list(data.keys()) == sorted(data.keys())
