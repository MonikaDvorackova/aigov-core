"""Deterministic governance replay for aigov.audit_export.v1 (via Rust replay engine)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _find_replay_binary() -> str | None:
    env = (os.environ.get("GOVAI_REPLAY_AUDIT_EXPORT_BIN") or "").strip()
    if env and Path(env).is_file():
        return env
    found = shutil.which("replay_audit_export_once")
    if found:
        return found
    root = Path(__file__).resolve().parents[2]
    target_root = Path(
        (os.environ.get("CARGO_TARGET_DIR") or "").strip() or str(root / "rust" / "target")
    )
    for candidate in (
        target_root / "debug" / "replay_audit_export_once",
        target_root / "release" / "replay_audit_export_once",
        root / "rust/target/debug/replay_audit_export_once",
        root / "rust/target/release/replay_audit_export_once",
    ):
        if candidate.is_file():
            return str(candidate)
    for rel in (
        "rust/target/debug/replay_audit_export_once",
        "rust/target/release/replay_audit_export_once",
    ):
        legacy = root / rel
        if legacy.is_file():
            return str(legacy)
    return None


def replay_audit_export(path: str | Path) -> dict[str, Any]:
    """
    Replay governance state from an on-disk audit export JSON file.

    Returns the structured ``ReplayResult`` document emitted by ``replay_audit_export_once``.
    """

    bin_path = _find_replay_binary()
    if not bin_path:
        raise RuntimeError(
            "replay_audit_export_once not found. Build with: "
            "cd rust && cargo build --bin replay_audit_export_once. "
            "Or set GOVAI_REPLAY_AUDIT_EXPORT_BIN."
        )
    p = Path(path)
    proc = subprocess.run(
        [bin_path, str(p)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        raise RuntimeError(
            proc.stderr.strip() or f"replay_audit_export_once exited {proc.returncode}"
        )
    out = json.loads(proc.stdout)
    if not isinstance(out, dict):
        raise RuntimeError("replay output must be a JSON object")
    return out


def format_replay_report(result: dict[str, Any], *, compact: bool = False) -> str:
    """Human-readable replay summary for CLI output."""

    lines = [
        "GovAI deterministic replay",
        f"run_id={result.get('run_id')}",
        f"event_count={result.get('event_count')}",
        f"exported_verdict={result.get('exported_verdict')}",
        f"reconstructed_verdict={result.get('reconstructed_verdict')}",
    ]
    integrity = result.get("integrity") or {}
    if isinstance(integrity, dict):
        lines.append(f"replay_integrity={integrity.get('replay_integrity')}")
        lines.append(f"replay_consistency={integrity.get('replay_consistency')}")
        lines.append(f"verdict_match={integrity.get('verdict_match')}")
    validation = result.get("validation") or {}
    if isinstance(validation, dict):
        errors = validation.get("errors") or []
        if errors:
            lines.append("validation_errors:")
            for err in errors:
                if isinstance(err, dict):
                    lines.append(f"  - {err.get('code')}: {err.get('message')}")
    projection = result.get("projection")
    if isinstance(projection, dict):
        expl = projection.get("explanation") or {}
        if isinstance(expl, dict):
            summary = expl.get("verdict_summary")
            if summary:
                lines.append(f"summary: {summary}")
            for item in expl.get("why_blocked") or []:
                lines.append(f"  blocked: {item}")
            for item in expl.get("what_unlocked_valid") or []:
                lines.append(f"  unlocked: {item}")
            gates = expl.get("gate_contributions") or []
            if gates:
                lines.append("gates:")
                for g in gates:
                    if isinstance(g, dict):
                        lines.append(
                            f"  - {g.get('gate')}: {g.get('status')} ({g.get('detail')})"
                        )
    if not compact:
        lines.append(f"determinism_digest={result.get('determinism_digest')}")
    return "\n".join(lines)
