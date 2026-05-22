"""Tests for scripts/validate_partner_ecosystem_manifest.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_partner_ecosystem_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_partner_ecosystem_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vpe_mod():
    return _load_mod()


def test_validate_real_manifest(vpe_mod):
    payload, code = vpe_mod.validate_manifest(REPO_ROOT, "docs/partners/partner-ecosystem-manifest.json")
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    assert payload["failures"] == []
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    raw = vpe_mod.dumps_json(payload)
    assert json.loads(raw) == payload
    assert list(json.loads(raw).keys()) == sorted(json.loads(raw).keys())


def test_validate_missing_manifest(vpe_mod, tmp_path: Path):
    payload, code = vpe_mod.validate_manifest(tmp_path, "docs/partners/partner-ecosystem-manifest.json")
    assert code == 1
    assert payload["ok"] is False
    assert payload["errors"]


def test_validate_missing_required_field(vpe_mod, tmp_path: Path):
    bad = tmp_path / "m.json"
    bad.write_text(
        json.dumps(
            {
                "partner_program": {
                    "summary": "x" * 30,
                },
            }
        ),
        encoding="utf-8",
    )
    payload, code = vpe_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert payload["ok"] is False
    assert any("missing_required_key" in e for e in payload["errors"])


def test_validate_missing_referenced_doc(vpe_mod, tmp_path: Path):
    doc = {
        "accreditation_levels": [
            {
                "id": "a",
                "name": "A",
                "summary": "Summary text long enough for validation rules.",
            }
        ],
        "audit_requirements": ["audit one"],
        "certification_program": {"summary": "Certification program summary text here."},
        "certification_requirements": ["req one"],
        "co_selling": {"summary": "Co-selling summary text long enough here."},
        "implementation_services": {"summary": "Implementation services summary text here."},
        "non_goals": ["not a goal"],
        "partner_program": {"summary": "Partner program summary text long enough."},
        "partner_types": [{"description": "Description text long enough for partner type.", "id": "x"}],
        "referenced_documents": [{"path": "missing-partner-doc.md", "role": "r"}],
        "referenced_examples": [{"path": "missing-ex-partner.sh", "role": "e"}],
        "required_checks": ["check-one"],
        "revenue_sharing": {"summary": "Revenue sharing summary text long enough."},
        "training_tracks": [
            {
                "id": "t",
                "name": "T",
                "summary": "Training track summary text long enough.",
            }
        ],
    }
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps(doc), encoding="utf-8")
    payload, code = vpe_mod.validate_manifest(tmp_path, "m.json")
    assert code == 1
    assert payload["ok"] is False
    assert any(
        "referenced_document_missing" in e or "referenced_example_missing" in e for e in payload["errors"]
    )


def test_subprocess_json_roundtrip():
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "validate_partner_ecosystem_manifest.py"),
            "--json",
            "--repo-root",
            str(REPO_ROOT),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["ok"] is True
    assert list(data.keys()) == sorted(data.keys())
