"""Tests for scripts/iso_42001_readiness_check.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "iso_42001_readiness_check.py"
    spec = importlib.util.spec_from_file_location("iso_42001_readiness_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def iso_mod():
    return _load_mod()


def test_compute_real_repo_ok(iso_mod):
    payload, code = iso_mod.compute_iso_42001_readiness(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert payload["failures"] == []


def test_landing_conservative_iso_framing(iso_mod):
    landing = (REPO_ROOT / iso_mod.LANDING_PATH).read_text(encoding="utf-8")
    assert "ISO/IEC 42001" in landing
    assert "Aligned" in landing
    assert "not certification" in landing.lower()


def test_forbidden_certified_claim_fails(iso_mod, tmp_path: Path):
    root = tmp_path / "repo"
    (root / "docs/standards").mkdir(parents=True)
    (root / "docs/standards/iso-42001-readiness.md").write_text(
        "## Purpose\n## Readiness framing\n## Validation\n",
        encoding="utf-8",
    )
    (root / "dashboard/lib/landing").mkdir(parents=True)
    (root / "dashboard/lib/landing/landingPageContent.ts").write_text(
        "ISO/IEC 42001 certified product\nAligned\nnot certification\n",
        encoding="utf-8",
    )
    for rel in iso_mod.SCAN_PATHS:
        if rel == iso_mod.LANDING_PATH:
            continue
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("not certification\n", encoding="utf-8")
    (root / "Makefile").write_text("iso-42001-readiness-check:\n", encoding="utf-8")
    payload, code = iso_mod.compute_iso_42001_readiness(root)
    assert code == 1
    assert payload["ok"] is False
    assert any("iso_certified" in f or "42001_certified" in f for f in payload["failures"])
