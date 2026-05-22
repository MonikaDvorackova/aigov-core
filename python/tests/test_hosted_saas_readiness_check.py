"""Tests for scripts/hosted_saas_readiness_check.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "hosted_saas_readiness_check.py"
    spec = importlib.util.spec_from_file_location("hosted_saas_readiness_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def saas_mod():
    return _load_mod()


def test_run_check_real_repo(saas_mod):
    payload, code = saas_mod.run_check(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert "govbase_service_manifest" in {c["name"] for c in payload["checks"]}
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    assert payload["checks"] == sorted(payload["checks"], key=lambda c: c["name"])
    assert not payload["failures"]


def test_run_check_missing_repo(saas_mod, tmp_path: Path):
    payload, code = saas_mod.run_check(tmp_path)
    assert code == 1
    assert payload["ok"] is False


def test_onboarding_flow_step_ids(saas_mod):
    saas_mod._validate_onboarding_flow(REPO_ROOT, "hosted-saas/onboarding-flow.json")


def test_tenant_persistence_stack(saas_mod):
    saas_mod._validate_tenant_persistence(REPO_ROOT)
