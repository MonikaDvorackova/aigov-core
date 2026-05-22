from __future__ import annotations

import pytest

from aigov_py.runtime.client import HttpRequestSpec, RuntimeGovernanceClient, compliance_summary_url
from aigov_py.runtime.exceptions import EvidenceIngestRejected, ValidationError
from aigov_py.runtime.models import (
    ComplianceSummary,
    ComplianceVerdict,
    EvidenceEvent,
    EvidenceIngestResult,
)


def test_evidence_event_validation_and_wire() -> None:
    ev = EvidenceEvent(
        event_id=" e1 ",
        event_type="model_trained",
        ts_utc="2026-01-01T00:00:00Z",
        actor="a",
        system="s",
        run_id="r1",
        payload={"k": "v"},
        environment=" staging ",
    )
    wire = ev.to_wire_dict()
    assert wire["event_id"] == "e1"
    assert wire["environment"] == "staging"
    assert wire["payload"] == {"k": "v"}

    with pytest.raises(ValueError):
        EvidenceEvent(
            event_id="",
            event_type="t",
            ts_utc="ts",
            actor="a",
            system="s",
            run_id="r",
            payload={},
        )


def test_evidence_ingest_result_from_response() -> None:
    body = {
        "ok": True,
        "record_hash": "h",
        "policy_version": "pv",
        "environment": "ci",
        "extra": 1,
    }
    r = EvidenceIngestResult.from_response(body)
    assert r.record_hash == "h"
    assert r.raw["extra"] == 1

    with pytest.raises(ValueError):
        EvidenceIngestResult.from_response({"ok": False})


def test_compliance_summary_parsing() -> None:
    ok_body = {
        "ok": True,
        "schema_version": "aigov.compliance_summary.v2",
        "policy_version": "pv",
        "run_id": "rid",
        "verdict": "VALID",
        "current_state": {"schema_version": "aigov.compliance_current_state.v2"},
    }
    s = ComplianceSummary.from_response(ok_body)
    assert s.ok is True
    assert s.verdict == ComplianceVerdict.VALID
    assert s.current_state is not None

    bad = {
        "ok": False,
        "schema_version": "aigov.compliance_summary.v2",
        "policy_version": "pv",
        "run_id": "rid",
        "error": "run_not_found",
        "code": "not_found",
        "message": "missing",
    }
    s2 = ComplianceSummary.from_response(bad)
    assert s2.ok is False
    assert s2.verdict is None


class _FakeTransport:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.calls: list[HttpRequestSpec] = []

    def request_json(self, spec: HttpRequestSpec, *, timeout_sec: float | None = None) -> dict:
        self.calls.append(spec)
        return self.responses.pop(0)


def test_runtime_client_uses_transport() -> None:
    ft = _FakeTransport(
        [
            {"ok": True, "record_hash": "rh", "policy_version": "p", "environment": "ci"},
            {
                "ok": True,
                "schema_version": "aigov.compliance_summary.v2",
                "policy_version": "p",
                "run_id": "r1",
                "verdict": "BLOCKED",
                "current_state": {},
            },
        ]
    )
    client = RuntimeGovernanceClient("http://127.0.0.1:8088", transport=ft)
    ev = EvidenceEvent(
        event_id="1",
        event_type="t",
        ts_utc="ts",
        actor="a",
        system="s",
        run_id="r1",
        payload={},
    )
    out = client.submit_evidence(ev)
    assert out.record_hash == "rh"
    assert ft.calls[0].method == "POST"
    assert "/evidence" in ft.calls[0].url

    summary = client.get_compliance_summary("r1")
    assert summary.verdict == ComplianceVerdict.BLOCKED
    assert ft.calls[1].method == "GET"
    assert "run_id=r1" in ft.calls[1].url


def test_submit_evidence_rejected() -> None:
    ft = _FakeTransport([{"ok": False, "error": "dup", "message": "duplicate", "code": "dup"}])
    client = RuntimeGovernanceClient("http://127.0.0.1:8088", transport=ft)
    ev = EvidenceEvent(
        event_id="1",
        event_type="t",
        ts_utc="ts",
        actor="a",
        system="s",
        run_id="r1",
        payload={},
    )
    with pytest.raises(EvidenceIngestRejected):
        client.submit_evidence(ev)


def test_client_base_url_validation() -> None:
    with pytest.raises(ValidationError):
        RuntimeGovernanceClient("not-a-url")
    with pytest.raises(ValidationError):
        RuntimeGovernanceClient("http://127.0.0.1:8088", timeout_sec=0.0)


def test_compliance_summary_url_encodes() -> None:
    u = compliance_summary_url("http://x.test", "a b")
    assert "run_id=a+b" in u or "run_id=a%20b" in u
