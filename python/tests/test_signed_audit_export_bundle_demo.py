"""Snapshot test for committed signed audit export bundle demo fixture."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "examples/signed-audit-export-bundle/demo.valid.zip"
TRUST = ROOT / "examples/signed-audit-export-bundle/trust-demo.json"
SNAPSHOT = ROOT / "examples/signed-audit-export-bundle/expected-verification.snapshot.json"
BINARY = ROOT / "rust/target/debug/verify_audit_export_bundle_once"


@pytest.fixture(scope="module")
def verifier_binary() -> Path:
    if not BINARY.is_file():
        subprocess.run(
            ["cargo", "build", "--bin", "verify_audit_export_bundle_once"],
            cwd=ROOT / "rust",
            check=True,
        )
    assert BINARY.is_file(), "verify_audit_export_bundle_once missing after build"
    return BINARY


def _verify(verifier_binary: Path) -> dict:
    env = os.environ.copy()
    env["AIGOV_POLICY_TRUST_ED25519_JSON"] = TRUST.read_text(encoding="utf-8")
    proc = subprocess.run(
        [str(verifier_binary), "--json", str(BUNDLE)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = json.loads(proc.stdout)
    assert isinstance(out, dict)
    return out


def test_demo_bundle_verifies_success(verifier_binary: Path) -> None:
    result = _verify(verifier_binary)
    assert result["overall_status"] == "success"
    assert result["signature_verified"] is True
    assert result["canonical_bundle_digest_verified"] is True
    assert result["replay_validation_passed"] is True
    assert result["unsigned_dependency_detected"] is False


def test_demo_bundle_matches_snapshot(verifier_binary: Path) -> None:
    result = _verify(verifier_binary)
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    for key in expected:
        assert result.get(key) == expected[key], f"mismatch on {key}"


def test_generate_script_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "demo.zip"
    trust = tmp_path / "trust.json"
    proc = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts/generate_signed_audit_export_bundle_demo.py"),
            "--out",
            str(out),
            "--trust-out",
            str(trust),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.returncode == 0
    assert out.is_file()
    assert trust.is_file()
