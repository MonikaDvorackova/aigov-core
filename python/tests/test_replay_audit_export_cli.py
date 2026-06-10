"""CLI wrapper tests for replay-audit-export (requires replay_audit_export_once binary)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUST_DIR = REPO_ROOT / "rust"
TARGET_DIR = RUST_DIR / "target"
BINARY = TARGET_DIR / "debug" / "replay_audit_export_once"


@pytest.fixture(scope="module")
def replay_binary() -> str:
    if not BINARY.is_file():
        env = os.environ.copy()
        env["CARGO_TARGET_DIR"] = str(TARGET_DIR)
        subprocess.run(
            ["cargo", "build", "--bin", "replay_audit_export_once"],
            cwd=RUST_DIR,
            check=True,
            env=env,
        )
    assert BINARY.is_file(), "replay_audit_export_once missing after build"
    return str(BINARY)


def test_replay_wrapper_invokes_binary(replay_binary: str, tmp_path: Path, monkeypatch) -> None:
    from aigov_py import replay_audit_export as mod

    monkeypatch.setenv("GOVAI_REPLAY_AUDIT_EXPORT_BIN", replay_binary)
    export_path = REPO_ROOT / "docs/examples/audit_export_v1.example.json"
    if not export_path.is_file():
        pytest.skip("example export missing")
    raw = json.loads(export_path.read_text(encoding="utf-8"))
    events = raw.get("evidence_events") or []
    if not events:
        pytest.skip("example export has no evidence_events")
    run_id = (raw.get("run") or {}).get("run_id") or "run-123"
    from aigov_py.portable_evidence_digest import portable_evidence_digest_v1

    raw["evidence_hashes"]["events_content_sha256"] = portable_evidence_digest_v1(
        str(run_id), events
    )
    chain = []
    prev = None
    for i, ev in enumerate(sorted(events, key=lambda e: (e.get("ts_utc"), e.get("event_id")))):
        rh = f"{i+1:064x}"
        chain.append(
            {
                "event_id": ev["event_id"],
                "ts_utc": ev["ts_utc"],
                "event_type": ev["event_type"],
                "prev_hash": prev,
                "record_hash": rh,
            }
        )
        prev = rh
    raw["evidence_hashes"]["log_chain"] = chain
    p = tmp_path / "export.json"
    p.write_text(json.dumps(raw) + "\n", encoding="utf-8")
    result = mod.replay_audit_export(p)
    assert "reconstructed_verdict" in result
    assert result.get("event_count", 0) >= 1
    text = mod.format_replay_report(result)
    assert "reconstructed_verdict" in text
