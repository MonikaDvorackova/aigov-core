"""Tests for scripts/evidence_quality_score.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_SAMPLE = {
    "evidence_quality_score": 97,
    "findings": [
        "limitations_documented",
        "lineage_multi_parent_declared",
        "provenance_checksum_coverage_partial",
        "retention_posture_explicit",
        "transformations_fully_referenced",
    ],
    "lineage_score": 100,
    "ok": True,
    "provenance_score": 92,
    "recommendations": [
        "refresh_snapshot_after_material_dataset_changes",
        "register_sha256_checksums_for_all_dataset_sources",
        "rerun_validators_in_ci_on_snapshot_updates",
    ],
    "retention_score": 100,
    "risk_level": "low",
}


def _load_mod():
    path = REPO_ROOT / "scripts" / "evidence_quality_score.py"
    spec = importlib.util.spec_from_file_location("evidence_quality_score", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def score_mod():
    return _load_mod()


def test_score_sample_stable(score_mod):
    raw = (REPO_ROOT / "examples/evidence-quality/sample-dataset-provenance-snapshot.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    payload, code = score_mod.score_from_dict(data)
    assert code == 0
    assert payload == EXPECTED_SAMPLE


def test_score_invalid_schema(score_mod):
    payload, code = score_mod.score_from_dict({})
    assert code == 1
    assert payload["ok"] is False
    assert payload["risk_level"] == "high"
    assert set(payload.keys()) == {
        "evidence_quality_score",
        "findings",
        "lineage_score",
        "ok",
        "provenance_score",
        "recommendations",
        "retention_score",
        "risk_level",
    }
