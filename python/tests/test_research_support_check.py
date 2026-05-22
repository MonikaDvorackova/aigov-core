"""Tests for scripts/research_support_check.py and manuscript_evidence_runner.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_research_support_subprocess_json():
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "research_support_check.py"), "--json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["ok"] is True
    assert "checked_paths" in data


def test_manuscript_runner_writes_artifacts(tmp_path: Path):
    out = tmp_path / "evidence-out"
    env = os.environ.copy()
    env["MANUSCRIPT_EVIDENCE_DIR"] = str(out)
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "manuscript_evidence_runner.py")],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert (out / "microbenchmark-results.json").is_file()
    assert (out / "research-support-check.json").is_file()
    mb = json.loads((out / "microbenchmark-results.json").read_text(encoding="utf-8"))
    assert mb["ok"] is True


@pytest.mark.parametrize(
    "script",
    [
        "legal_positioning_check.py",
        "privacy_architecture_check.py",
        "provider_cooperation_check.py",
        "scalability_patterns_check.py",
    ],
)
def test_bundle_validator_scripts_json(script: str):
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / script), "--json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["ok"] is True
