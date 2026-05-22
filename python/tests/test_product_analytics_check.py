"""Tests for scripts/product_analytics_check.py and validate_product_analytics_manifest."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_pa():
    path = REPO_ROOT / "scripts" / "product_analytics_check.py"
    spec = importlib.util.spec_from_file_location("product_analytics_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_vm():
    path = REPO_ROOT / "scripts" / "validate_product_analytics_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_product_analytics_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pa_mod():
    return _load_pa()


@pytest.fixture(scope="module")
def vm_mod():
    return _load_vm()


def test_compute_product_analytics_real_repo(pa_mod):
    payload, code = pa_mod.compute_product_analytics(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert payload["version"] == 1
    assert payload["failures"] == []
    assert payload["warnings"] == []
    raw = pa_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_validate_manifest_real_repo(vm_mod):
    payload, code = vm_mod.validate_manifest(REPO_ROOT, "product-analytics/product-analytics-manifest.json")
    assert code == 0
    assert payload["ok"] is True


def test_validate_manifest_missing(vm_mod, tmp_path: Path):
    payload, code = vm_mod.validate_manifest(tmp_path, "product-analytics/product-analytics-manifest.json")
    assert code == 1
    assert payload["ok"] is False


def test_product_analytics_subprocess_json(pa_mod):
    import subprocess

    r = subprocess.run(
        ["python3", str(REPO_ROOT / "scripts" / "product_analytics_check.py"), "--json", "--repo-root", str(REPO_ROOT)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["ok"] is True
