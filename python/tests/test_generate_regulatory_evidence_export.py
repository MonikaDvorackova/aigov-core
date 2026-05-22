"""Tests for scripts/generate_regulatory_evidence_export.py."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_regulatory_evidence_export.py"
    spec = importlib.util.spec_from_file_location("generate_regulatory_evidence_export", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gen_mod():
    return _load_mod()


def test_generate_markdown_stable_digest(gen_mod):
    rel = "docs/regulatory/regulatory-evidence-manifest.json"
    md = gen_mod.generate_markdown(REPO_ROOT, rel)
    assert md.startswith("# GovAI regulatory evidence export\n")
    assert "## AI Act obligations index" in md
    assert "ai_act_article_9_risk_management_system" in md
    assert "## Export metadata" in md
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == "bca43744a5605cde6f34115e8f86c7a1057587d6797c4f98e85eb1aac9b5a1df"

