"""Tests for scripts/validate_customer_health_sample.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_customer_health_sample.py"
    spec = importlib.util.spec_from_file_location("validate_customer_health_sample", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vhs_mod():
    return _load_mod()


def test_validate_real_sample(vhs_mod):
    payload, code = vhs_mod.validate_sample(REPO_ROOT, "examples/customer-analytics/sample-customer-health.json")
    assert code == 0
    assert payload["ok"] is True
    assert payload["failures"] == []
    raw = vhs_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_schema_errors_sorted(vhs_mod):
    assert vhs_mod.schema_errors({}) == sorted(vhs_mod.schema_errors({}))


def test_validate_missing_sample(vhs_mod, tmp_path: Path):
    payload, code = vhs_mod.validate_sample(tmp_path, "examples/customer-analytics/sample-customer-health.json")
    assert code == 1
    assert payload["ok"] is False


def test_subprocess_json_roundtrip(vhs_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "validate_customer_health_sample.py"),
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
