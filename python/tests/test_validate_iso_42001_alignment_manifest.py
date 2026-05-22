"""Tests for scripts/validate_iso_42001_alignment_manifest.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_iso_42001_alignment_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_iso_42001_alignment_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_mod()


def test_validate_real_manifest(mod):
    rel = "docs/standards/iso-42001-alignment-manifest.json"
    payload, code = mod.validate_manifest(REPO_ROOT, rel)
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    assert payload["failures"] == []
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_validate_missing_manifest(mod, tmp_path: Path):
    payload, code = mod.validate_manifest(tmp_path, "docs/standards/iso-42001-alignment-manifest.json")
    assert code == 1
    assert payload["ok"] is False
    assert payload["errors"]


def test_validate_missing_required_key(mod, tmp_path: Path):
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps({"version": 1, "summary": "x" * 30}), encoding="utf-8")
    payload, code = mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert payload["ok"] is False
    assert any("missing_required_key" in e for e in payload["errors"])
