"""Tests for scripts/hosted_platform_check.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "hosted_platform_check.py"
    spec = importlib.util.spec_from_file_location("hosted_platform_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def hp_mod():
    return _load_mod()


def test_run_check_real_repo(hp_mod):
    payload, code = hp_mod.run_check(
        REPO_ROOT,
        "docs/hosted-platform/hosted-platform-manifest.json",
        "examples/hosted-platform/sample-hosted-readiness-snapshot.json",
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    names = sorted(c["name"] for c in payload["checks"])
    assert names == sorted(
        [
            "documentation_paths",
            "example_drivers",
            "hosted_readiness_score",
            "hosted_saas_bundle",
            "makefile_wiring",
            "manifest_validation",
            "snapshot_validation",
        ]
    )
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    assert payload["checks"] == sorted(payload["checks"], key=lambda c: c["name"])
    assert not payload["failures"]


def test_run_check_missing_repo_root_paths(hp_mod, tmp_path: Path):
    payload, code = hp_mod.run_check(
        tmp_path,
        "docs/hosted-platform/hosted-platform-manifest.json",
        "examples/hosted-platform/sample-hosted-readiness-snapshot.json",
    )
    assert code == 1
    assert payload["ok"] is False


def test_validate_production_readiness_bundle_real_repo(hp_mod):
    payload, code = hp_mod.validate_production_readiness_bundle(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert sorted(c["name"] for c in payload["checks"]) == [
        "production_readiness_checklist",
        "production_readiness_doc",
    ]
