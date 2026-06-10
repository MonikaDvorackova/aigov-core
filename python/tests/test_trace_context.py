"""Tests for W3C trace context helpers."""

from aigov_py.trace_context import attach_external_trace, parse_traceparent

VALID = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"


def test_parse_traceparent_valid() -> None:
    ctx = parse_traceparent(VALID)
    assert ctx is not None
    assert ctx["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert ctx["span_id"] == "00f067aa0ba902b7"


def test_parse_traceparent_invalid() -> None:
    assert parse_traceparent("not-a-traceparent") is None


def test_attach_external_trace() -> None:
    out = attach_external_trace({"step": 1}, VALID)
    assert "external_trace" in out
    assert out["external_trace"]["trace_id"]
