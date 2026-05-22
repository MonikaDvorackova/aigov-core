"""Smoke tests for empirical benchmark runner scripts (stdlib, quick mode)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

SCRIPTS = (
    "run_event_ingestion_benchmarks.py",
    "run_hash_chain_benchmarks.py",
    "run_export_benchmarks.py",
    "run_storage_benchmarks.py",
    "run_multi_tenant_benchmarks.py",
    "run_failure_benchmarks.py",
)

EXPECTED = {
    "run_event_ingestion_benchmarks.py": "event-ingestion-benchmarks.json",
    "run_hash_chain_benchmarks.py": "hash-chain-benchmarks.json",
    "run_export_benchmarks.py": "export-benchmarks.json",
    "run_storage_benchmarks.py": "storage-benchmarks.json",
    "run_multi_tenant_benchmarks.py": "multi-tenant-benchmarks.json",
    "run_failure_benchmarks.py": "failure-benchmarks.json",
}


@pytest.fixture
def quick_env():
    return {**os.environ, "GOVAI_EMPIRICAL_QUICK": "1"}


@pytest.mark.parametrize("script", SCRIPTS)
def test_benchmark_script_writes_json(script, tmp_path, quick_env):
    out = tmp_path / script.replace(".py", "")
    out.mkdir()
    cp = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / script), "--out-dir", str(out), "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=quick_env,
    )
    assert cp.returncode == 0, cp.stderr
    fname = EXPECTED[script]
    p = out / fname
    assert p.is_file()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("ok") is True


def test_empirical_benchmark_lib_report_rel_path_outside_repo(tmp_path):
    import importlib.util

    path = REPO_ROOT / "scripts" / "empirical_benchmark_lib.py"
    spec = importlib.util.spec_from_file_location("empirical_benchmark_lib", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ext = tmp_path / "x.json"
    ext.write_text("{}", encoding="utf-8")
    s = mod.report_rel_path(REPO_ROOT, ext)
    assert str(ext) == s


    import importlib.util

    path = REPO_ROOT / "scripts" / "empirical_benchmark_lib.py"
    spec = importlib.util.spec_from_file_location("empirical_benchmark_lib", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    samples = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    st = mod.latency_stats_ms(samples)
    assert st["count"] == 10
    assert st["min_ms"] == 1.0
    assert st["max_ms"] == 10.0
    assert st["median_ms"] == 5.5
