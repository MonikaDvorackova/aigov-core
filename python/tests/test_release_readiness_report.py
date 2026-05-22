"""Tests for scripts/release_readiness_report.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "release_readiness_report.py"
    spec = importlib.util.spec_from_file_location("release_readiness_report", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_compute_report_ok():
    mod = _load_mod()
    payload, code = mod.compute_report(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = mod.dumps_json(payload)
    data = json.loads(raw)
    assert list(data.keys()) == sorted(data.keys())
    assert data["ok"] is True


def test_subprocess_release_readiness_report_json():
    r = subprocess.run(
        ["python3", str(REPO_ROOT / "scripts" / "release_readiness_report.py"), "--json", "--repo-root", str(REPO_ROOT)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
