"""Tests for scripts/multi_tenant_check.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "multi_tenant_check.py"
    spec = importlib.util.spec_from_file_location("multi_tenant_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mt_mod():
    return _load_mod()


def test_run_check_real_repo_full(mt_mod):
    payload, code = mt_mod.run_check(
        REPO_ROOT,
        "multi-tenant/governance-manifest.json",
        tenant_isolation_only=False,
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert payload["tenant_isolation_only"] is False
    names = sorted(c["name"] for c in payload["checks"])
    assert names == sorted(
        [
            "delegated_administration",
            "documentation_paths",
            "environment_segmentation",
            "example_drivers",
            "governance_manifest",
            "makefile_wiring",
            "role_hierarchy",
            "sample_tenant_governance_snapshot",
            "separation_of_duties",
            "tenant_isolation_model",
        ]
    )
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    assert payload["checks"] == sorted(payload["checks"], key=lambda c: c["name"])
    assert not payload["failures"]


def test_run_check_tenant_isolation_only(mt_mod):
    payload, code = mt_mod.run_check(
        REPO_ROOT,
        "multi-tenant/governance-manifest.json",
        tenant_isolation_only=True,
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["tenant_isolation_only"] is True
    names = sorted(c["name"] for c in payload["checks"])
    assert names == sorted(
        [
            "governance_manifest",
            "makefile_wiring",
            "tenant_isolation_model",
        ]
    )
    assert not payload["failures"]


def test_run_check_missing_repo_root_paths(mt_mod, tmp_path: Path):
    payload, code = mt_mod.run_check(
        tmp_path,
        "multi-tenant/governance-manifest.json",
        tenant_isolation_only=False,
    )
    assert code == 1
    assert payload["ok"] is False
