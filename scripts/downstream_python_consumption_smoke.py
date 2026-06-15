#!/usr/bin/env python3
"""Downstream Python consumption smoke: fresh venv + non-editable pip install from ./python."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_PKG = ROOT / "python"
BUNDLE = ROOT / "examples/signed-audit-export-bundle/demo.valid.zip"
TRUST = ROOT / "examples/signed-audit-export-bundle/trust-demo.json"
STANDARDS = ROOT / "examples/standards/evidence-pack.valid.json"


def _venv_bins(venv_dir: Path) -> tuple[Path, Path]:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe", venv_dir / "Scripts" / "govai.exe"
    return venv_dir / "bin" / "python", venv_dir / "bin" / "govai"


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout, file=sys.stderr)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        raise SystemExit(f"command failed ({proc.returncode}): {' '.join(cmd)}")
    return proc


def main() -> int:
    for path in (PYTHON_PKG, BUNDLE, TRUST, STANDARDS):
        if not path.exists():
            print(f"missing required path: {path}", file=sys.stderr)
            return 1

    with tempfile.TemporaryDirectory(prefix="govai-downstream-py-") as tmp:
        venv_dir = Path(tmp) / "venv"
        venv.create(venv_dir, with_pip=True)
        py, govai = _venv_bins(venv_dir)

        _run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
        _run([str(py), "-m", "pip", "install", str(PYTHON_PKG)])

        import_probe = """
import govai
from govai import GovAIClient, __version__
import aigov_py.standards.cli
assert GovAIClient is not None
assert __version__
print("imports_ok")
"""
        proc = subprocess.run([str(py), "-c", import_probe], capture_output=True, text=True)
        if proc.returncode != 0 or "imports_ok" not in proc.stdout:
            if proc.stderr:
                print(proc.stderr, file=sys.stderr)
            print("import probe failed", file=sys.stderr)
            return 1

        _run([str(govai), "--help"])

        standards_proc = _run(
            [str(govai), "standards", "validate-evidence-pack", str(STANDARDS)],
        )
        payload = json.loads(standards_proc.stdout)
        if not payload.get("ok"):
            print(f"standards validation failed: {payload}", file=sys.stderr)
            return 1

        env = os.environ.copy()
        env["AIGOV_POLICY_TRUST_ED25519_JSON"] = TRUST.read_text(encoding="utf-8")
        verifier_bin = ROOT / "rust" / "target" / "debug" / "verify_audit_export_bundle_once"
        if not verifier_bin.is_file():
            print(
                f"missing verifier binary: {verifier_bin} "
                "(run: cd rust && cargo build --bin verify_audit_export_bundle_once)",
                file=sys.stderr,
            )
            return 1
        env["GOVAI_VERIFY_AUDIT_EXPORT_BUNDLE_BIN"] = str(verifier_bin)
        verify_proc = _run(
            [
                str(govai),
                "verify-evidence-pack",
                "--bundle",
                str(BUNDLE),
                "--json",
            ],
            env=env,
        )
        verify_result = json.loads(verify_proc.stdout)
        if verify_result.get("overall_status") != "success":
            print(f"bundle verification failed: {verify_result}", file=sys.stderr)
            return 1

    print("downstream Python consumption smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
