"""Tests for scripts/generate_marketplace_listing.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_marketplace_listing.py"
    spec = importlib.util.spec_from_file_location("generate_marketplace_listing", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gml_mod():
    return _load_mod()


def test_render_listing_deterministic(gml_mod):
    md1 = gml_mod.render_listing(REPO_ROOT, "examples/marketplace/sample-extension-package.json")
    md2 = gml_mod.render_listing(REPO_ROOT, "examples/marketplace/sample-extension-package.json")
    assert md1 == md2
    assert "## Summary" in md1
    assert "govai-sample-policy-pack" in md1
    assert "## Artifacts" in md1
    assert "policy-module-example.json" in md1


def test_render_listing_sorted_publisher_keys(gml_mod):
    md = gml_mod.render_listing(REPO_ROOT, "examples/marketplace/sample-extension-package.json")
    idx_display = md.index("display_name")
    idx_id = md.index("id")
    assert idx_display < idx_id
