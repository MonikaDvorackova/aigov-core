from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest


def _read_req_payload(req: object) -> dict:
    data = getattr(req, "data", None)
    assert isinstance(data, (bytes, bytearray))
    return json.loads(data.decode("utf-8"))


def test_ai_discovery_completed_emits_expected_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUN_ID", "local-govai-check-test")
    monkeypatch.setenv("AIGOV_AUDIT_URL", "http://127.0.0.1:8088")
    monkeypatch.setenv("AIGOV_ACTOR", "tester")
    monkeypatch.setenv("AIGOV_SYSTEM", "unit")

    import aigov_py.ai_discovery_completed as mod

    fake_resp = MagicMock()
    fake_resp.read.return_value = b'{"ok":true,"record_hash":"h"}'
    fake_resp.__enter__.return_value = fake_resp
    fake_resp.__exit__.return_value = False

    with patch("aigov_py.ai_discovery_completed.urllib.request.urlopen", return_value=fake_resp) as urlopen:
        mod.main()

    req = urlopen.call_args[0][0]
    payload = _read_req_payload(req)
    assert payload["event_id"] == "ai_discovery_completed_local-govai-check-test"
    assert payload["event_type"] == "ai_discovery_reported"
    assert payload["run_id"] == "local-govai-check-test"
    assert payload["actor"] == "tester"
    assert payload["system"] == "unit"
    p = payload["payload"]
    assert p["status"] == "completed"
    assert p["openai"] is False
    assert p["transformers"] is False
    assert p["model_artifacts"] is False
    assert p["source"] == "local_flow"


def test_ai_discovery_completed_is_idempotent_on_duplicate_409(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RUN_ID", "r1")
    monkeypatch.setenv("AIGOV_AUDIT_URL", "http://127.0.0.1:8088")

    import aigov_py.ai_discovery_completed as mod

    err = urllib.error.HTTPError(
        url="http://127.0.0.1:8088/evidence",
        code=409,
        msg="Conflict",
        hdrs=None,
        fp=None,
    )
    with patch("aigov_py.ai_discovery_completed.urllib.request.urlopen", side_effect=err):
        mod.main()

