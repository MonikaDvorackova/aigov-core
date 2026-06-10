"""Tests for runtime diagnostics CLI."""

from __future__ import annotations

import json
from unittest.mock import patch

from aigov_py.runtime_diagnostics import run_runtime_diagnostics


def test_runtime_diagnostics_all_pass() -> None:
    def fake_get(url: str, *, timeout_sec: float) -> tuple[int, object]:
        _ = timeout_sec
        if url.endswith("/health"):
            return 200, {"ok": True}
        if url.endswith("/ready"):
            return 200, {"ok": True, "ready": True}
        if url.endswith("/status"):
            return 200, {
                "ok": True,
                "runtime_version": "0.2.1",
                "environment": "dev",
                "configuration": {"ledger_dir_configured": True},
                "readiness_components": {"ledger_writable": True},
            }
        return 404, {}

    with patch("aigov_py.runtime_diagnostics._get_json", side_effect=fake_get):
        code = run_runtime_diagnostics("http://127.0.0.1:8088", json_out=True)
    assert code == 0


def test_runtime_diagnostics_ready_fail() -> None:
    def fake_get(url: str, *, timeout_sec: float) -> tuple[int, object]:
        _ = timeout_sec
        if url.endswith("/ready"):
            return 503, {"ok": False, "message": "NOT_READY"}
        if url.endswith("/health"):
            return 200, {"ok": True}
        return 200, {"ok": True}

    with patch("aigov_py.runtime_diagnostics._get_json", side_effect=fake_get):
        code = run_runtime_diagnostics("http://127.0.0.1:8088", json_out=True)
    assert code == 1
