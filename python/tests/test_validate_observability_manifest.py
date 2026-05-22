"""Tests for scripts/validate_observability_manifest.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_observability_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_observability_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vom_mod():
    return _load_mod()


def test_validate_real_manifest(vom_mod):
    rel = "docs/observability/observability-manifest.json"
    payload, code = vom_mod.validate_manifest(REPO_ROOT, rel)
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    assert payload["failures"] == []
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = vom_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_validate_missing_manifest(vom_mod, tmp_path: Path):
    payload, code = vom_mod.validate_manifest(tmp_path, "docs/observability/observability-manifest.json")
    assert code == 1
    assert payload["ok"] is False
    assert payload["errors"]


def test_validate_missing_required_key(vom_mod, tmp_path: Path):
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps({"version": 1, "summary": "x" * 30}), encoding="utf-8")
    payload, code = vom_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert payload["ok"] is False
    assert any("missing_required_key" in e for e in payload["errors"])


def test_validate_score_weights_must_sum_to_100(vom_mod, tmp_path: Path):
    manifest = {
        "boundaries": {
            "billing": "no",
            "data": "no",
            "enforcement": "no",
            "ledger": "no",
            "summary": "Boundary summary text long enough for validation.",
        },
        "evidence_flow_signals": [
            {"guide": "docs/g.md", "id": "e", "summary": "Evidence summary long enough for rules."}
        ],
        "non_goals": ["ng"],
        "operational_probes": [
            {"command": "c", "description": "desc long enough", "name": "n"}
        ],
        "readiness_signals": [
            {"guide": "docs/g.md", "id": "r", "summary": "Readiness summary long enough rules."}
        ],
        "referenced_documents": [{"path": "docs/d.md", "role": "r"}],
        "referenced_examples": [{"path": "docs/e.md", "role": "r"}],
        "required_checks": ["make x"],
        "runtime_health_signals": [
            {"guide": "docs/g.md", "id": "h", "summary": "Health summary long enough for rules."}
        ],
        "score_weights": {
            "diagnostics": 10,
            "evidence_flow": 10,
            "readiness": 10,
            "runtime_health": 10,
        },
        "snapshot_schema": {
            "required_collections": ["a"],
            "required_keys": ["x"],
            "summary": "Snapshot summary long enough for the validator rules.",
        },
        "summary": "Manifest summary text long enough for rules.",
        "version": 1,
    }
    for rel, content in (
        ("m.json", json.dumps(manifest)),
        ("docs/d.md", "# d\n"),
        ("docs/e.md", "# e\n"),
        ("docs/g.md", "# g\n"),
    ):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    payload, code = vom_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert any("score_weights_sum_not_100" in e for e in payload["errors"])


def test_validate_signal_guide_missing(vom_mod, tmp_path: Path):
    manifest = {
        "boundaries": {
            "billing": "no",
            "data": "no",
            "enforcement": "no",
            "ledger": "no",
            "summary": "Boundary summary text long enough for validation.",
        },
        "evidence_flow_signals": [
            {"guide": "docs/missing.md", "id": "e", "summary": "Evidence summary long enough."}
        ],
        "non_goals": ["ng"],
        "operational_probes": [
            {"command": "c", "description": "desc long enough", "name": "n"}
        ],
        "readiness_signals": [
            {"guide": "docs/g.md", "id": "r", "summary": "Readiness summary long enough rules."}
        ],
        "referenced_documents": [{"path": "docs/d.md", "role": "r"}],
        "referenced_examples": [{"path": "docs/e.md", "role": "r"}],
        "required_checks": ["make x"],
        "runtime_health_signals": [
            {"guide": "docs/g.md", "id": "h", "summary": "Health summary long enough for rules."}
        ],
        "score_weights": {
            "diagnostics": 25,
            "evidence_flow": 25,
            "readiness": 20,
            "runtime_health": 30,
        },
        "snapshot_schema": {
            "required_collections": ["a"],
            "required_keys": ["x"],
            "summary": "Snapshot summary long enough for the validator rules.",
        },
        "summary": "Manifest summary text long enough for rules.",
        "version": 1,
    }
    for rel, content in (
        ("m.json", json.dumps(manifest)),
        ("docs/d.md", "# d\n"),
        ("docs/e.md", "# e\n"),
        ("docs/g.md", "# g\n"),
    ):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    payload, code = vom_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert any("signal_guide_missing" in e for e in payload["errors"])
