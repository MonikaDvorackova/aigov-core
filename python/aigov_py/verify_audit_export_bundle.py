"""Offline verification for signed audit export zip bundles (Rust verifier)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _find_verify_binary() -> str | None:
    env = (os.environ.get("GOVAI_VERIFY_AUDIT_EXPORT_BUNDLE_BIN") or "").strip()
    if env and Path(env).is_file():
        return env
    found = shutil.which("verify_audit_export_bundle_once")
    if found:
        return found
    root = Path(__file__).resolve().parents[2]
    target_root = Path(
        (os.environ.get("CARGO_TARGET_DIR") or "").strip() or str(root / "rust" / "target")
    )
    for candidate in (
        target_root / "debug" / "verify_audit_export_bundle_once",
        target_root / "release" / "verify_audit_export_bundle_once",
        root / "rust/target/debug/verify_audit_export_bundle_once",
        root / "rust/target/release/verify_audit_export_bundle_once",
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def verify_audit_export_bundle(
    bundle_path: str | Path,
    *,
    json_output: bool = True,
    expected_issuer_id: str | None = None,
) -> dict[str, Any]:
    """
    Verify a signed audit export zip bundle offline.

    Returns the structured verification document from ``verify_audit_export_bundle_once``.
    """

    bin_path = _find_verify_binary()
    if not bin_path:
        raise RuntimeError(
            "verify_audit_export_bundle_once not found. Build with: "
            "cd rust && cargo build --bin verify_audit_export_bundle_once. "
            "Or set GOVAI_VERIFY_AUDIT_EXPORT_BUNDLE_BIN."
        )
    cmd = [bin_path]
    if json_output:
        cmd.append("--json")
    if expected_issuer_id:
        cmd.extend(["--expected-issuer-id", expected_issuer_id.strip()])
    cmd.append(str(Path(bundle_path)))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 and not proc.stdout.strip():
        raise RuntimeError(
            proc.stderr.strip()
            or f"verify_audit_export_bundle_once exited {proc.returncode}"
        )
    out = json.loads(proc.stdout)
    if not isinstance(out, dict):
        raise RuntimeError("verification output must be a JSON object")
    return out
