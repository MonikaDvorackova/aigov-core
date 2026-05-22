"""Tests for scripts/validate_standardization_readiness_snapshot.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_standardization_readiness_snapshot.py"
    spec = importlib.util.spec_from_file_location("validate_standardization_readiness_snapshot", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_mod()


def test_validate_sample_snapshot(mod):
    payload, code = mod.validate_snapshot(
        REPO_ROOT,
        "examples/launch/sample-standardization-readiness-snapshot.json",
    )
    assert code == 0
    assert payload["ok"] is True
    raw = mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_missing_snapshot(mod, tmp_path: Path):
    payload, code = mod.validate_snapshot(tmp_path, "missing.json")
    assert code == 1
    assert "snapshot_missing" in str(payload["errors"])


def test_invalid_enum(mod, tmp_path: Path):
    p = tmp_path / "s.json"
    p.write_text(
        json.dumps(
            {
                "captured_at": "2026-05-13T00:00:00Z",
                "certification": {
                    "disclaimer_acknowledged": True,
                    "human_approval_gate_documented": True,
                },
                "documentation": {
                    "index_linked": True,
                    "launch_docs_complete": True,
                    "readme_public_section": True,
                },
                "ecosystem": {
                    "ci_artifacts_defined": True,
                    "example_scripts_present": True,
                    "make_targets_defined": True,
                },
                "risks": {"open_blocking_issues": 0, "open_warnings": 0},
                "schema_version": 1,
                "snapshot_id": "x",
                "standardization": {
                    "interchange_conformance": "nope",
                    "policy_pack_examples": "ready",
                    "registry_alignment": "ready",
                },
            }
        ),
        encoding="utf-8",
    )
    payload, code = mod.validate_snapshot(tmp_path, "s.json")
    assert code == 1
    assert any("invalid_enum" in e for e in payload["errors"])
