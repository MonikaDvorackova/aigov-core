"""CLI wrapper tests for epistemic-readiness (requires epistemic_readiness_once binary)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TARGET_DIR = ROOT / "rust" / "target"
BINARY = TARGET_DIR / "debug" / "epistemic_readiness_once"


@pytest.fixture(scope="module", autouse=True)
def _build_binary() -> None:
    if not BINARY.is_file():
        subprocess.run(
            ["cargo", "build", "--bin", "epistemic_readiness_once"],
            cwd=ROOT / "rust",
            check=True,
        )
    assert BINARY.is_file(), "epistemic_readiness_once missing after build"


def test_epistemic_readiness_cli_json(tmp_path: Path) -> None:
    export = {
        "ok": True,
        "schema_version": "aigov.audit_export.v0",
        "policy_version": "p1",
        "run": {"run_id": "r1"},
        "evidence_events": [],
        "decision": {"verdict": "BLOCKED"},
        "evidence_hashes": {"events_content_sha256": "0" * 64, "log_chain": []},
    }
    p = tmp_path / "export.json"
    p.write_text(json.dumps(export), encoding="utf-8")
    env = {**os.environ, "GOVAI_EPISTEMIC_READINESS_BIN": str(BINARY)}
    proc = subprocess.run(
        [sys.executable, "-m", "aigov_py.cli", "epistemic-readiness", "--export", str(p), "--json"],
        cwd=ROOT / "python",
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode != 0
    out = json.loads(proc.stdout)
    assert out.get("schema_version") == "aigov.epistemic_readiness.v1"
    assert out.get("status") == "not_ready"
