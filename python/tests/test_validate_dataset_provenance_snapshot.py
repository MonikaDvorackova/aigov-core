"""Tests for scripts/validate_dataset_provenance_snapshot.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_dataset_provenance_snapshot.py"
    spec = importlib.util.spec_from_file_location("validate_dataset_provenance_snapshot", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def snap_mod():
    return _load_mod()


def test_schema_errors_empty_for_sample(snap_mod):
    raw = (REPO_ROOT / "examples/evidence-quality/sample-dataset-provenance-snapshot.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert snap_mod.schema_errors(data) == []


def test_validate_sample_snapshot(snap_mod):
    payload, code = snap_mod.validate_snapshot(
        REPO_ROOT, "examples/evidence-quality/sample-dataset-provenance-snapshot.json"
    )
    assert code == 0
    assert payload["ok"] is True


def test_schema_errors_not_object(snap_mod):
    assert snap_mod.schema_errors([]) == ["root_not_object"]
