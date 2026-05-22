"""Tests for scripts/regulatory_evidence_check.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "regulatory_evidence_check.py"
    spec = importlib.util.spec_from_file_location("regulatory_evidence_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rec_mod():
    return _load_mod()


def test_run_check_real_repo(rec_mod):
    payload, code = rec_mod.run_check(REPO_ROOT, "docs/regulatory/regulatory-evidence-manifest.json")
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    names = sorted(c["name"] for c in payload["checks"])
    assert names == ["makefile_wiring", "manifest_validation", "obligations_validation"]
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    assert not payload["failures"]
