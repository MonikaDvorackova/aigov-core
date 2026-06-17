"""Derived epistemic readiness for aigov.audit_export.v1 (via Rust evaluator)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _find_binary() -> str | None:
    env = (os.environ.get("GOVAI_EPISTEMIC_READINESS_BIN") or "").strip()
    if env and Path(env).is_file():
        return env
    found = shutil.which("epistemic_readiness_once")
    if found:
        return found
    root = Path(__file__).resolve().parents[2]
    target_root = Path(
        (os.environ.get("CARGO_TARGET_DIR") or "").strip() or str(root / "rust" / "target")
    )
    for candidate in (
        target_root / "debug" / "epistemic_readiness_once",
        target_root / "release" / "epistemic_readiness_once",
        root / "rust/target/debug/epistemic_readiness_once",
        root / "rust/target/release/epistemic_readiness_once",
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def epistemic_readiness_from_export(path: str | Path) -> dict[str, Any]:
    """
    Evaluate epistemic readiness from an on-disk audit export JSON file.

    Returns the structured ``aigov.epistemic_readiness.v1`` document emitted by
    ``epistemic_readiness_once``.
    """

    bin_path = _find_binary()
    if not bin_path:
        raise RuntimeError(
            "epistemic_readiness_once not found. Build with: "
            "cd rust && cargo build --bin epistemic_readiness_once. "
            "Or set GOVAI_EPISTEMIC_READINESS_BIN."
        )
    p = Path(path)
    proc = subprocess.run(
        [bin_path, str(p)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode not in (0, 1) and not proc.stdout.strip():
        raise RuntimeError(
            proc.stderr.strip() or f"epistemic_readiness_once exited {proc.returncode}"
        )
    out = json.loads(proc.stdout)
    if not isinstance(out, dict):
        raise RuntimeError("epistemic readiness output must be a JSON object")
    return out


def format_epistemic_summary(report: dict[str, Any]) -> str:
    """Human-readable epistemic readiness summary for CLI output."""

    lines = [
        "GovAI epistemic readiness (derived, non-authoritative)",
        f"run_id={report.get('decision_knowledge', {}).get('run_id')}",
        f"status={report.get('status')}",
        f"compliance_verdict_valid={report.get('compliance_verdict_valid')}",
        f"reconstructable={report.get('reconstructable')}",
        f"coverage={report.get('coverage', {}).get('ratio')}",
        f"confidence={report.get('confidence', {}).get('level')} "
        f"(non_authoritative={report.get('confidence', {}).get('non_authoritative')})",
    ]
    gaps = report.get("readiness_gaps") or []
    if gaps:
        lines.append("readiness_gaps:")
        for gap in gaps:
            lines.append(f"  - {gap}")
    return "\n".join(lines)
