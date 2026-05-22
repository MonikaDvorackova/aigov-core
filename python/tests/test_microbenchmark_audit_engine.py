"""Tests for scripts/microbenchmark_audit_engine.py."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mb():
    path = REPO_ROOT / "scripts" / "microbenchmark_audit_engine.py"
    spec = importlib.util.spec_from_file_location("microbenchmark_audit_engine", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mb():
    return _load_mb()


def test_record_hash_matches_rust_style(mb):
    prev = mb.GENESIS
    event_json = '{"a":1}'
    h = hashlib.sha256()
    h.update(prev.encode())
    h.update(b"\n")
    h.update(event_json.encode())
    assert mb.record_hash(prev, event_json) == h.hexdigest()


def test_run_benchmarks_ok_and_schema(mb):
    out = mb.run_benchmarks(chain_len=50, seed=7, throughput_warmup=10)
    assert out["ok"] is True
    assert set(out.keys()) >= {"assumptions", "benchmarks", "checked_paths", "ok", "version"}
    assert out["version"] == 1
    assert "event_creation_throughput_events_per_sec" in out["benchmarks"]


def test_subprocess_json_roundtrip():
    import subprocess

    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "microbenchmark_audit_engine.py"), "--json", "--chain-len", "30"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["ok"] is True
