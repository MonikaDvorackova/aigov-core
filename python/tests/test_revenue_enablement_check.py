"""Tests for scripts/revenue_enablement_check.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "revenue_enablement_check.py"
    spec = importlib.util.spec_from_file_location("revenue_enablement_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def re_mod():
    return _load_mod()


def test_compute_real_repo(re_mod):
    payload, code = re_mod.compute_revenue_enablement(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = re_mod.dumps_json(payload)
    data = json.loads(raw)
    assert list(data.keys()) == sorted(data.keys())


def test_subprocess_json(re_mod):
    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "revenue_enablement_check.py"),
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
    out = json.loads(r.stdout.strip())
    assert out["ok"] is True
    _ = re_mod
