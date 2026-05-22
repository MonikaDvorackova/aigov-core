"""Tests for scripts/empirical_evaluation_check.py and orchestrated benchmark outputs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


@pytest.fixture
def empirical_env():
    e = {**os.environ, "GOVAI_EMPIRICAL_QUICK": "1"}
    return e


def test_full_evaluation_and_check_passes(tmp_path, empirical_env):
    out = tmp_path / "bench"
    out.mkdir()
    full = _run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_full_empirical_evaluation.py"), "--out-dir", str(out)],
        env=empirical_env,
    )
    assert full.returncode == 0, full.stderr
    for name in (
        "event-ingestion-benchmarks.json",
        "hash-chain-benchmarks.json",
        "export-benchmarks.json",
        "storage-benchmarks.json",
        "multi-tenant-benchmarks.json",
        "failure-benchmarks.json",
        "empirical-evaluation-summary.json",
    ):
        assert (out / name).is_file()

    chk = _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "empirical_evaluation_check.py"),
            "--json",
            "--benchmark-dir",
            str(out),
        ],
        env=empirical_env,
    )
    assert chk.returncode == 0, chk.stderr + chk.stdout
    data = json.loads(chk.stdout)
    assert data.get("ok") is True
    assert not data.get("failures")


def test_evaluation_check_fails_when_summary_ok_false(tmp_path, empirical_env):
    out = tmp_path / "bench2"
    out.mkdir()
    _run(
        [sys.executable, str(REPO_ROOT / "scripts" / "run_full_empirical_evaluation.py"), "--out-dir", str(out)],
        env=empirical_env,
    )
    summary = json.loads((out / "empirical-evaluation-summary.json").read_text(encoding="utf-8"))
    summary["ok"] = False
    (out / "empirical-evaluation-summary.json").write_text(
        json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    chk = _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "empirical_evaluation_check.py"),
            "--json",
            "--benchmark-dir",
            str(out),
        ],
        env=empirical_env,
    )
    assert chk.returncode == 1
    data = json.loads(chk.stdout)
    assert data.get("ok") is False
