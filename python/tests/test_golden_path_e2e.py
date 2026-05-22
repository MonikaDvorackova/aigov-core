"""
End-to-end golden path: local audit service + artefact submit/verify + govai check => VALID.

Requires Postgres (DATABASE_URL), same shape as compliance `make_verify` / govai-ci.
"""

from __future__ import annotations

import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from aigov_py.demo_golden_path import generate_demo_golden_path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _wait_audit_ready(proc: subprocess.Popen, base_url: str, timeout_s: float = 180.0) -> None:
    deadline = time.monotonic() + timeout_s
    ready = f"{base_url.rstrip('/')}/ready"
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            pytest.fail(f"audit service exited early with code {proc.returncode}")
        try:
            with urllib.request.urlopen(ready, timeout=2) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
            pass
        time.sleep(0.5)
    pytest.fail(f"GET {ready} did not return HTTP 200 within {timeout_s}s")


@pytest.fixture
def audit_base_url(tmp_path: Path) -> str:
    db_url = (os.environ.get("DATABASE_URL") or "").strip()
    if not db_url:
        pytest.skip("DATABASE_URL not set (need Postgres for golden path e2e)")

    repo = _repo_root()
    rust_dir = repo / "rust"
    subprocess.run(
        ["cargo", "build", "--locked", "--bin", "aigov_audit"],
        cwd=str(rust_dir),
        check=True,
    )
    bin_path = rust_dir / "target" / "debug" / "aigov_audit"
    ledger = tmp_path / "govai-ledger"
    ledger.mkdir(parents=True, exist_ok=True)

    bind = "127.0.0.1:18088"
    base = f"http://{bind}"

    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": db_url,
            "GOVAI_LEDGER_DIR": str(ledger),
            "GOVAI_API_KEYS_JSON": '{"ci-test-api-key":"github-actions"}',
            "GOVAI_AUTO_MIGRATE": "true",
            "AIGOV_ENVIRONMENT": "dev",
            "AIGOV_BIND": bind,
            "AIGOV_POLICY_DIR": str(rust_dir.resolve()),
        }
    )

    proc = subprocess.Popen(
        [str(bin_path)],
        env=env,
        cwd=str(rust_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_audit_ready(proc, base)
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def test_golden_path_e2e_valid_verdict(audit_base_url: str, tmp_path: Path) -> None:
    run_id = "00000000-0000-4000-8000-00000000e2e1"
    artefacts = tmp_path / "artefacts"
    generate_demo_golden_path(run_id=run_id, output_dir=artefacts)

    env = os.environ.copy()
    env["GOVAI_AUDIT_BASE_URL"] = audit_base_url
    env["GOVAI_API_KEY"] = "ci-test-api-key"
    env["GOVAI_PROJECT"] = "github-actions"

    subprocess.run(
        [
            "govai",
            "--project",
            "github-actions",
            "submit-evidence-pack",
            "--path",
            str(artefacts),
            "--run-id",
            run_id,
        ],
        check=True,
        env=env,
    )
    subprocess.run(
        [
            "govai",
            "--project",
            "github-actions",
            "verify-evidence-pack",
            "--path",
            str(artefacts),
            "--run-id",
            run_id,
            "--require-export",
        ],
        check=True,
        env=env,
    )
    completed = subprocess.run(
        ["govai", "check", "--run-id", run_id],
        capture_output=True,
        text=True,
        env=env,
    )
    out = completed.stdout + completed.stderr
    assert completed.returncode == 0, out
    first = (out.splitlines() or [""])[0].strip()
    assert first == "VALID", out
