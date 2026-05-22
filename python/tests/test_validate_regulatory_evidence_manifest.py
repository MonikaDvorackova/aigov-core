"""Tests for scripts/validate_regulatory_evidence_manifest.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_regulatory_evidence_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_regulatory_evidence_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vrm_mod():
    return _load_mod()


def test_validate_real_manifest(vrm_mod):
    rel = "docs/regulatory/regulatory-evidence-manifest.json"
    payload, code = vrm_mod.validate_manifest(REPO_ROOT, rel)
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    assert payload["failures"] == []
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = vrm_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_validate_missing_manifest(vrm_mod, tmp_path: Path):
    payload, code = vrm_mod.validate_manifest(tmp_path, "docs/regulatory/regulatory-evidence-manifest.json")
    assert code == 1
    assert payload["ok"] is False
    assert payload["errors"]


def test_validate_missing_required_key(vrm_mod, tmp_path: Path):
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps({"version": 1, "summary": "x" * 30}), encoding="utf-8")
    payload, code = vrm_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert payload["ok"] is False
    assert any("missing_required_key" in e for e in payload["errors"])


def test_validate_bad_obligations_index_json(vrm_mod, tmp_path: Path):
    obl = tmp_path / "obl.json"
    obl.write_text("[]", encoding="utf-8")
    manifest = {
        "ai_act_mapping_scope": {
            "deployment_contexts": ["c"],
            "risk_focus": ["r"],
            "summary": "Scope summary text long enough for validation.",
        },
        "evidence_themes": [
            {
                "guide": "docs/g.md",
                "id": "t1",
                "summary": "Theme summary text long enough here.",
            }
        ],
        "non_goals": ["ng"],
        "obligations_index": "obl.json",
        "operational_probes": [
            {"command": "c", "description": "d text long enough", "name": "n"}
        ],
        "referenced_documents": [{"path": "docs/d.md", "role": "r"}],
        "referenced_examples": [{"path": "docs/e.md", "role": "r"}],
        "required_checks": ["make x"],
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

    payload, code = vrm_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert any("obligations_index_not_obligations_json" in e for e in payload["errors"])
