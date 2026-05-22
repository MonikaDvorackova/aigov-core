from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aigov_py.standards.cli import run_standards_command


def _govai_cli_available() -> bool:
    try:
        import nacl  # noqa: F401 — govai main CLI imports signing at module load time

        return True
    except ImportError:
        return False


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "aigov_py.standards.cli", *args],
        cwd=str(_repo_root() / "python"),
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_validate_capability_policy_example_ok() -> None:
    p = _repo_root() / "examples" / "standards" / "capability_policy.valid.json"
    cp = _run_cli("validate-capability-policy", str(p))
    assert cp.returncode == 0
    out = json.loads(cp.stdout.strip())
    assert out["ok"] is True
    assert out["digest"]


def test_cli_validate_capability_policy_invalid_exit_code() -> None:
    bad = {"schema_version": "x", "policy_id": "p", "tenant_scope": "t", "capabilities": []}
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(bad, f)
        path = f.name
    try:
        cp = _run_cli("validate-capability-policy", path)
        assert cp.returncode != 0
        out = json.loads(cp.stdout.strip())
        assert out["ok"] is False
    finally:
        Path(path).unlink(missing_ok=True)


def test_cli_digest_delegation_graph_ok() -> None:
    p = _repo_root() / "examples" / "standards" / "delegation_graph.valid.json"
    cp = _run_cli("digest", "delegation-graph", str(p))
    assert cp.returncode == 0
    out = json.loads(cp.stdout.strip())
    assert out["ok"] is True
    assert out["digest"].startswith("sha256:")


def test_cli_digest_unknown_kind_fails() -> None:
    p = _repo_root() / "examples" / "standards" / "capability_policy.valid.json"
    cp = _run_cli("digest", "unknown-kind", str(p))
    assert cp.returncode == 4
    out = json.loads(cp.stdout.strip())
    assert out["ok"] is False
    assert out["error"] == "unknown_kind"


def test_cli_missing_file_returns_json_and_exit_usage() -> None:
    cp = _run_cli("validate-capability-policy", "/no/such/standards/file.json")
    assert cp.returncode == 4
    out = json.loads(cp.stdout.strip())
    assert out["ok"] is False
    assert out["error"] == "file_not_found"


def test_cli_invalid_json_returns_exit_usage() -> None:
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write("{ not json ")
        path = f.name
    try:
        cp = _run_cli("validate-capability-policy", path)
        assert cp.returncode == 4
        out = json.loads(cp.stdout.strip())
        assert out["ok"] is False
        assert out["error"] == "invalid_json"
    finally:
        Path(path).unlink(missing_ok=True)


def test_cli_unsupported_extension_returns_json() -> None:
    import tempfile

    p = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    p.write("{}")
    path = p.name
    p.close()
    try:
        cp = _run_cli("validate-capability-policy", path)
        assert cp.returncode == 4
        out = json.loads(cp.stdout.strip())
        assert out["ok"] is False
        assert out["error"] == "unsupported_format"
    finally:
        Path(path).unlink(missing_ok=True)


def test_cli_malformed_root_array_returns_malformed_root() -> None:
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write("[1,2]")
        path = f.name
    try:
        cp = _run_cli("validate-capability-policy", path)
        assert cp.returncode == 4
        out = json.loads(cp.stdout.strip())
        assert out["ok"] is False
        assert out["error"] == "malformed_root"
    finally:
        Path(path).unlink(missing_ok=True)


def test_run_standards_command_wrong_standard_kind(capsys: pytest.CaptureFixture[str]) -> None:
    ex = _repo_root() / "examples" / "standards"
    rc = run_standards_command("validate-capability-policy", str(ex / "delegation_graph.valid.json"))
    assert rc == 4
    out = json.loads(capsys.readouterr().out.strip())
    assert out["error"] == "wrong_standard_kind"
    assert out["inferred_kind"] == "delegation-graph"
    assert out["expected_kind"] == "capability-policy"


@pytest.mark.skipif(not _govai_cli_available(), reason="govai CLI requires PyNaCl at import time")
def test_govai_standards_validate_capability_policy_ok() -> None:
    p = _repo_root() / "examples" / "standards" / "capability_policy.valid.json"
    cp = subprocess.run(
        [sys.executable, "-m", "aigov_py.cli", "standards", "validate-capability-policy", str(p)],
        cwd=str(_repo_root() / "python"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0
    out = json.loads(cp.stdout.strip())
    assert out["ok"] is True


@pytest.mark.skipif(not _govai_cli_available(), reason="govai CLI requires PyNaCl at import time")
def test_govai_standards_wrong_standard_kind() -> None:
    p = _repo_root() / "examples" / "standards" / "delegation_graph.valid.json"
    cp = subprocess.run(
        [sys.executable, "-m", "aigov_py.cli", "standards", "validate-capability-policy", str(p)],
        cwd=str(_repo_root() / "python"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 4
    out = json.loads(cp.stdout.strip())
    assert out["ok"] is False
    assert out["error"] == "wrong_standard_kind"
