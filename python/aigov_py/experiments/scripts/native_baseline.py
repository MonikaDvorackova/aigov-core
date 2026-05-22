#!/usr/bin/env python3
"""
Native CI baseline for RWCI: no GovAI CLI, no audit HTTP calls, no GovAI secrets.

Prints exactly one line each (parseable by the runner):
  RWCI_BASELINE_METHOD=<method>
  RWCI_BASELINE_TYPE=<native_ci_detected|fallback_minimal>

Methods (native_ci_detected): pytest, make_test, npm_test, cargo_test
Methods (fallback_minimal): compileall, noop

Detection order:
  1. pytest layout / config
  2. Makefile ``test`` target
  3. package.json ``scripts.test``
  4. Cargo.toml (Rust)
  5. Fallback: ``python -m compileall .`` (fallback_minimal / compileall), or noop if nothing to run.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def _emit(method: str, btype: str) -> None:
    print(f"RWCI_BASELINE_METHOD={method}")
    print(f"RWCI_BASELINE_TYPE={btype}")


def _write_github_output(key: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"{key}={value}\n")


def _has_pytest_signals(root: Path) -> bool:
    if (root / "pytest.ini").is_file():
        return True
    if (root / "tox.ini").is_file():
        return True
    py = root / "pyproject.toml"
    if py.is_file():
        try:
            txt = py.read_text(encoding="utf-8", errors="replace")
        except OSError:
            txt = ""
        if "[tool.pytest" in txt or "[pytest]" in txt.lower():
            return True
    tests = root / "tests"
    if tests.is_dir():
        for p in tests.iterdir():
            if p.is_file() and p.name.startswith("test_") and p.suffix == ".py":
                return True
            if p.is_dir() and list(p.glob("test_*.py")):
                return True
    for p in root.glob("test_*.py"):
        if p.is_file():
            return True
    return False


def _makefile_has_test(root: Path) -> bool:
    mf = root / "Makefile"
    if not mf.is_file():
        return False
    try:
        txt = mf.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(re.search(r"^\s*test\s*:", txt, re.MULTILINE))


def _package_json_has_test(root: Path) -> bool:
    pkg = root / "package.json"
    if not pkg.is_file():
        return False
    try:
        raw = pkg.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if '"test"' not in raw and "'test'" not in raw:
        return False
    return '"scripts"' in raw


def _has_cargo(root: Path) -> bool:
    return (root / "Cargo.toml").is_file()


def _run(cmd: list[str], *, cwd: Path) -> int:
    return subprocess.run(cmd, cwd=str(cwd), check=False).returncode


def main() -> int:
    scenario = os.environ.get("SCENARIO", "unknown")
    print(f"RWCI_CONTEXT_SCENARIO={scenario}")

    root = Path(".").resolve()

    # 1) pytest — install pytest only when this path is chosen (standard for CI runners).
    if _has_pytest_signals(root):
        _emit("pytest", "native_ci_detected")
        _write_github_output("baseline_method", "pytest")
        _write_github_output("baseline_type", "native_ci_detected")
        rc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pytest"],
            cwd=str(root),
            check=False,
        ).returncode
        if rc != 0:
            return rc
        return _run([sys.executable, "-m", "pytest", "-q", "--tb=no", "-x"], cwd=root)

    # 2) make test
    if _makefile_has_test(root):
        _emit("make_test", "native_ci_detected")
        _write_github_output("baseline_method", "make_test")
        _write_github_output("baseline_type", "native_ci_detected")
        return _run(["make", "test"], cwd=root)

    # 3) npm test (may fail without install; still repository-native signal).
    if _package_json_has_test(root):
        _emit("npm_test", "native_ci_detected")
        _write_github_output("baseline_method", "npm_test")
        _write_github_output("baseline_type", "native_ci_detected")
        return _run(["npm", "test"], cwd=root)

    # 4) cargo test
    if _has_cargo(root):
        _emit("cargo_test", "native_ci_detected")
        _write_github_output("baseline_method", "cargo_test")
        _write_github_output("baseline_type", "native_ci_detected")
        return _run(["cargo", "test", "--no-run"], cwd=root)

    # 5) Fallback: syntax-only compile (bounded; does not claim full native CI coverage).
    _emit("compileall", "fallback_minimal")
    _write_github_output("baseline_method", "compileall")
    _write_github_output("baseline_type", "fallback_minimal")
    return _run([sys.executable, "-m", "compileall", "-q", "."], cwd=root)


if __name__ == "__main__":
    raise SystemExit(main())
