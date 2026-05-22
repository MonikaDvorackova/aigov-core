"""Tests for scripts/hosted_readiness_score.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

CONTRACT_KEYS = frozenset(
    {
        "deployment_score",
        "findings",
        "hosted_readiness_score",
        "ok",
        "operations_score",
        "recommendations",
        "risk_level",
        "support_score",
        "tenant_onboarding_score",
        "version",
    }
)


def _load_mod():
    path = REPO_ROOT / "scripts" / "hosted_readiness_score.py"
    spec = importlib.util.spec_from_file_location("hosted_readiness_score", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def score_mod():
    return _load_mod()


def test_compute_score_sample_ok(score_mod):
    payload, code = score_mod.compute_score(
        REPO_ROOT,
        "examples/hosted-platform/sample-hosted-readiness-snapshot.json",
        "docs/hosted-platform/hosted-platform-manifest.json",
    )
    assert code == 0
    assert payload["ok"] is True
    assert payload["hosted_readiness_score"] == 100
    assert payload["risk_level"] == "low"
    assert payload["findings"] == sorted(payload["findings"])
    assert payload["recommendations"] == sorted(payload["recommendations"])
    assert "weights" in payload


def test_cli_json_contract():
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "hosted_readiness_score.py"),
            "--input",
            "examples/hosted-platform/sample-hosted-readiness-snapshot.json",
            "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert set(data.keys()) == CONTRACT_KEYS
