"""Tests for scripts/roi_calculator.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "roi_calculator.py"
    spec = importlib.util.spec_from_file_location("roi_calculator", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def roi_mod():
    return _load_mod()


def test_compute_roi_correctness(roi_mod):
    data = {"baseline_cost": 480000, "expected_savings": 120000, "implementation_cost": 80000}
    payload, code = roi_mod.compute_roi(data)
    assert code == 0
    assert payload["ok"] is True
    assert payload["annual_savings"] == 120000.0
    assert payload["implementation_cost"] == 80000.0
    assert payload["net_first_year_value"] == 40000.0
    assert payload["roi_ratio"] == 1.5
    assert payload["payback_months"] == 8.0
    raw = roi_mod.dumps_json(payload)
    parsed = json.loads(raw)
    assert parsed == payload
    assert list(parsed.keys()) == sorted(parsed.keys())


def test_negative_input_fails(roi_mod):
    data = {"baseline_cost": 0, "expected_savings": -1, "implementation_cost": 0}
    payload, code = roi_mod.compute_roi(data)
    assert code == 1
    assert payload["ok"] is False
    assert "invalid_or_negative:expected_savings" in payload["errors"]


def test_subprocess_sample_input(roi_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "roi_calculator.py"),
            "--input",
            str(REPO_ROOT / "examples" / "revenue" / "sample-roi-input.json"),
            "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    out = json.loads(r.stdout.strip())
    assert out["ok"] is True
    assert list(out.keys()) == sorted(out.keys())
