"""Tests for scripts/security_trust_check.py JSON and compute_security_trust."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "security_trust_check.py"
    spec = importlib.util.spec_from_file_location("security_trust_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def st_mod():
    return _load_mod()


def test_compute_security_trust_real_repo_stable_shape(st_mod):
    payload, code = st_mod.compute_security_trust(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["version"] == 2
    assert payload["min_bytes_threshold"] >= 64
    assert payload["score"] == 100
    assert payload["failures"] == []
    assert payload["warnings"] == []
    assert isinstance(payload["checked_paths"], list)
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    assert len(payload["checks"]) > 0
    for c in payload["checks"]:
        assert "category" in c
        assert "check_id" in c
        assert "ok" in c
        assert c["ok"] is True
    raw = st_mod.dumps_json(payload)
    parsed = json.loads(raw)
    assert parsed == payload
    assert list(parsed.keys()) == sorted(parsed.keys())


def test_compute_security_trust_empty_repo_fails_with_score(st_mod, tmp_path: Path):
    payload, code = st_mod.compute_security_trust(tmp_path)
    assert code == 1
    assert payload["ok"] is False
    assert payload["score"] < 100
    assert len(payload["failures"]) > 0
    assert isinstance(payload["warnings"], list)
    assert any(not c["ok"] for c in payload["checks"])


def test_json_stdout_roundtrip_fail(st_mod, tmp_path: Path):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "security_trust_check.py"),
            "--json",
            "--repo-root",
            str(tmp_path),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 1
    line = r.stdout.strip()
    data = json.loads(line)
    assert data["ok"] is False
    assert list(data.keys()) == sorted(data.keys())
    assert "score" in data
    assert "checked_paths" in data


def test_json_stdout_roundtrip_pass():
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "security_trust_check.py"),
            "--json",
            "--repo-root",
            str(REPO_ROOT),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["ok"] is True
    assert data["score"] == 100


def test_security_review_shell_script_smoke():
    import subprocess

    r = subprocess.run(
        ["bash", str(REPO_ROOT / "examples" / "security-review" / "run-security-review-check.sh")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "security-review-check: OK" in r.stdout
