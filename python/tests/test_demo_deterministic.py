from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aigov_py import cli_exit
from aigov_py.cli import main


def test_demo_deterministic_missing_base_url_exits_2(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GOVAI_AUDIT_BASE_URL", raising=False)
    monkeypatch.setenv("GOVAI_API_KEY", "secret")
    code = main(["run", "demo-deterministic"])
    assert code == cli_exit.EX_USAGE
    err = capsys.readouterr().err
    assert "Missing GOVAI_AUDIT_BASE_URL" in err


def test_demo_deterministic_missing_api_key_exits_2(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GOVAI_AUDIT_BASE_URL", "https://audit.example.test")
    monkeypatch.delenv("GOVAI_API_KEY", raising=False)
    code = main(["run", "demo-deterministic"])
    assert code == cli_exit.EX_USAGE
    err = capsys.readouterr().err
    assert "Missing GOVAI_API_KEY" in err


def test_demo_deterministic_happy_path_mocked_http(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GOVAI_AUDIT_BASE_URL", "https://audit.example.test")
    monkeypatch.setenv("GOVAI_API_KEY", "secret")
    monkeypatch.setenv("GOVAI_DEMO_RUN_ID", "550e8400-e29b-41d4-a716-446655440000")

    summary1 = {
        "ok": True,
        "verdict": "BLOCKED",
        "requirements": {
            "missing_evidence": [
                {"code": "risk_reviewed", "source": "policy"},
                {"code": "human_approved", "source": "policy"},
                {"code": "model_promoted", "source": "policy"},
            ]
        },
    }
    summary2 = {"ok": True, "verdict": "VALID"}
    export_payload = {"ok": True, "schema_version": "aigov.audit_export.v1", "run": {"run_id": "r1"}}

    with patch("aigov_py.cli.GovAIClient") as client_cls:
        client_cls.return_value = MagicMock()
        with patch("aigov_py.cli.submit_event", return_value={"ok": True}) as submit:
            with patch("aigov_py.cli.get_compliance_summary", side_effect=[summary1, summary2]):
                with patch("aigov_py.cli.export_run", return_value=export_payload):
                    code = main(["run", "demo-deterministic"])

    assert code == cli_exit.EX_OK
    out = capsys.readouterr().out

    # Transcript shape (stable/readable).
    assert "run_id: 550e8400-e29b-41d4-a716-446655440000" in out
    assert "(2/7) submit incomplete evidence" in out
    assert "(3/7) check decision (expect BLOCKED)" in out
    assert "verdict: BLOCKED" in out
    assert "(4/7) missing evidence:" in out
    assert "- risk_reviewed" in out
    assert "- human_approved" in out
    assert "- model_promoted" in out
    assert "(5/7) submit required evidence" in out
    assert "(6/7) check decision (expect VALID)" in out
    assert "verdict: VALID" in out
    assert "(7/7) export audit JSON" in out
    assert "exported: docs/demo/audit_export_550e8400-e29b-41d4-a716-446655440000.json" in out

    # Export file is written.
    export_path = tmp_path / "docs" / "demo" / "audit_export_550e8400-e29b-41d4-a716-446655440000.json"
    assert export_path.is_file()
    parsed = json.loads(export_path.read_text(encoding="utf-8"))
    assert parsed["ok"] is True

    # We submitted multiple events.
    assert submit.call_count >= 2

