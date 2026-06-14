"""Tests for scripts/generate_release_notes.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_release_notes.py"
    spec = importlib.util.spec_from_file_location("generate_release_notes", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def notes_mod():
    return _load_mod()


def test_generate_existing_version(notes_mod):
    notes, meta = notes_mod.render_release_notes("0.2.1", REPO_ROOT)
    assert "GovAI 0.2.1" in notes
    assert meta["warnings"] == []
    assert "Release packaging metadata" in notes or "## Added" in notes


def test_generate_missing_version_warns(notes_mod):
    notes, meta = notes_mod.render_release_notes("9.9.9", REPO_ROOT)
    assert meta["warnings"]
    assert "template-only" in notes
