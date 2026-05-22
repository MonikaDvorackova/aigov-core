"""Tests for scripts/generate_hosted_readiness_export.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_hosted_readiness_export.py"
    spec = importlib.util.spec_from_file_location("generate_hosted_readiness_export", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def exp_mod():
    return _load_mod()


def test_generate_markdown_deterministic(exp_mod):
    md = exp_mod.generate_markdown(
        REPO_ROOT,
        "examples/hosted-platform/sample-hosted-readiness-snapshot.json",
        "docs/hosted-platform/hosted-platform-manifest.json",
    )
    assert md.startswith("# GovAI hosted readiness summary\n")
    assert "## Readiness scores" in md
    assert "## Recommendations" in md
    md2 = exp_mod.generate_markdown(
        REPO_ROOT,
        "examples/hosted-platform/sample-hosted-readiness-snapshot.json",
        "docs/hosted-platform/hosted-platform-manifest.json",
    )
    assert md == md2
