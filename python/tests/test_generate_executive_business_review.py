"""Tests for scripts/generate_executive_business_review.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_executive_business_review.py"
    spec = importlib.util.spec_from_file_location("generate_executive_business_review", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ebr_mod():
    return _load_mod()


def test_render_ebr_deterministic(ebr_mod):
    raw = (REPO_ROOT / "examples/customer-analytics/sample-customer-health.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    md1 = ebr_mod.render_ebr(data)
    md2 = ebr_mod.render_ebr(data)
    assert md1 == md2
    assert "# Executive business review" in md1
    assert "cust_sample_acme_001" in md1
    assert "| Health | 70 |" in md1
    assert "| Renewal signal | medium |" in md1


def test_render_ebr_invalid(ebr_mod):
    md = ebr_mod.render_ebr({})
    assert "Input validation failed" in md


def test_subprocess_stdout_stable(ebr_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "generate_executive_business_review.py"),
            "--input",
            str(REPO_ROOT / "examples/customer-analytics/sample-customer-health.json"),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert r.stdout == ebr_mod.render_ebr(json.loads((REPO_ROOT / "examples/customer-analytics/sample-customer-health.json").read_text(encoding="utf-8")))
