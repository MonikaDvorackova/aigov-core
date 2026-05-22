"""Tests for scripts/validate_evidence_quality_manifest.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_evidence_quality_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_evidence_quality_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vm_mod():
    return _load_mod()


def test_validate_real_manifest(vm_mod):
    payload, code = vm_mod.validate_manifest(REPO_ROOT, "docs/evidence-quality/evidence-quality-manifest.json")
    assert code == 0
    assert payload["ok"] is True
    assert payload["failures"] == []
    raw = vm_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_validate_missing_manifest(vm_mod, tmp_path: Path):
    payload, code = vm_mod.validate_manifest(tmp_path, "missing.json")
    assert code == 1
    assert payload["ok"] is False
