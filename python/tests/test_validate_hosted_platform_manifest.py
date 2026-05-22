"""Tests for scripts/validate_hosted_platform_manifest.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_hosted_platform_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_hosted_platform_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def man_mod():
    return _load_mod()


def test_validate_manifest_real_repo(man_mod):
    payload, code = man_mod.validate_manifest(
        REPO_ROOT,
        "docs/hosted-platform/hosted-platform-manifest.json",
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    assert not payload["failures"]


def test_validate_manifest_missing_file(man_mod, tmp_path: Path):
    payload, code = man_mod.validate_manifest(tmp_path, "docs/hosted-platform/hosted-platform-manifest.json")
    assert code == 1
    assert payload["ok"] is False
