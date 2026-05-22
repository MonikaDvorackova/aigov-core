"""Tests for scripts/validate_agent_governance_manifest.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_agent_governance_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_agent_governance_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vgm_mod():
    return _load_mod()


def test_validate_real_manifest(vgm_mod):
    rel = "docs/agent-governance/agent-governance-manifest.json"
    payload, code = vgm_mod.validate_manifest(REPO_ROOT, rel)
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    assert payload["failures"] == []
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = vgm_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_validate_missing_manifest(vgm_mod, tmp_path: Path):
    payload, code = vgm_mod.validate_manifest(tmp_path, "docs/agent-governance/agent-governance-manifest.json")
    assert code == 1
    assert payload["ok"] is False
    assert payload["errors"]
