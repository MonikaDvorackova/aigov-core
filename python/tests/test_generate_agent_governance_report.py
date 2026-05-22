"""Tests for scripts/generate_agent_governance_report.py."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "generate_agent_governance_report.py"
    spec = importlib.util.spec_from_file_location("generate_agent_governance_report", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gen_mod():
    return _load_mod()


def test_generate_markdown_structure(gen_mod):
    md = gen_mod.generate_markdown(
        REPO_ROOT,
        "examples/agent-governance/sample-agent-delegation-snapshot.json",
        "docs/agent-governance/agent-governance-manifest.json",
    )
    assert md.startswith("# GovAI multi-agent governance report\n")
    assert "## Snapshot metadata" in md
    assert "## Governance scores" in md
    assert "## Delegation" in md
    assert "## Approval chain" in md
    assert "## Override governance" in md
    assert "## Auditability" in md
    assert "## Findings" in md
    assert "## Recommendations" in md
    assert "## Report metadata" in md
    assert md.endswith("\n")


def test_generate_markdown_stable_digest(gen_mod):
    md = gen_mod.generate_markdown(
        REPO_ROOT,
        "examples/agent-governance/sample-agent-delegation-snapshot.json",
        "docs/agent-governance/agent-governance-manifest.json",
    )
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == "acc161d947ff628920574034418db6d8c9a7900e59db5574b1f882fd95ad87dd"
