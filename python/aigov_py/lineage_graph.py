"""Governance lineage graph from aigov.audit_export.v1 (via Rust lineage_graph_once)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _find_lineage_binary() -> str | None:
    env = (os.environ.get("GOVAI_LINEAGE_GRAPH_BIN") or "").strip()
    if env and Path(env).is_file():
        return env
    found = shutil.which("lineage_graph_once")
    if found:
        return found
    root = Path(__file__).resolve().parents[2]
    target_root = Path(
        (os.environ.get("CARGO_TARGET_DIR") or "").strip() or str(root / "rust" / "target")
    )
    for candidate in (
        target_root / "debug" / "lineage_graph_once",
        target_root / "release" / "lineage_graph_once",
        root / "rust/target/debug/lineage_graph_once",
        root / "rust/target/release/lineage_graph_once",
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def lineage_graph_from_export(path: str | Path, *, mermaid: bool = False) -> Any:
    bin_path = _find_lineage_binary()
    if not bin_path:
        raise RuntimeError(
            "lineage_graph_once not found. Build with: "
            "cd rust && cargo build --bin lineage_graph_once. "
            "Or set GOVAI_LINEAGE_GRAPH_BIN."
        )
    p = Path(path)
    cmd = [bin_path]
    if mermaid:
        cmd.append("--mermaid")
    cmd.append(str(p))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 and not proc.stdout.strip():
        raise RuntimeError(
            proc.stderr.strip() or f"lineage_graph_once exited {proc.returncode}"
        )
    if mermaid:
        return proc.stdout
    out = json.loads(proc.stdout)
    if not isinstance(out, dict):
        raise RuntimeError("lineage graph output must be a JSON object")
    return out


def format_lineage_summary(doc: dict[str, Any]) -> str:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    graph = doc.get("graph") if isinstance(doc.get("graph"), dict) else {}
    validation = (
        graph.get("lineage_validation")
        if isinstance(graph.get("lineage_validation"), dict)
        else {}
    )
    lines = [
        "GovAI lineage governance graph",
        f"run_id={summary.get('run_id', graph.get('run_id'))}",
        f"root_run_id={summary.get('root_run_id', graph.get('root_run_id'))}",
        f"lineage_integrity={summary.get('lineage_integrity_status', graph.get('lineage_integrity_status'))}",
        f"nodes={summary.get('node_count', len(graph.get('nodes') or []))}",
        f"edges={summary.get('edge_count', len(graph.get('edges') or []))}",
        f"delegation_types={graph.get('delegation_types', [])}",
        f"governance_gates={graph.get('governance_gates', [])}",
        f"orphaned_delegated_runs={validation.get('orphaned_delegated_runs', [])}",
        f"missing_parent_runs={validation.get('missing_parent_runs', [])}",
        f"delegation_cycle_detected={validation.get('delegation_cycle_detected', False)}",
    ]
    errors = validation.get("errors") or []
    if errors:
        lines.append("lineage_errors:")
        for e in errors[:10]:
            if isinstance(e, dict):
                lines.append(f"  - {e.get('code')}: {e.get('message')}")
    return "\n".join(lines)
