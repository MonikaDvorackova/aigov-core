"""LangChain-oriented helpers (stdlib + :class:`EvidenceEvent` only).

Wire these callables from LangChain callbacks or runnables in your application;
this module does **not** import LangChain at load time.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from aigov_py.runtime.models import EvidenceEvent


def utc_ts() -> str:
    """RFC3339-ish UTC timestamp with ``Z`` suffix (matches common evidence examples)."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_tool_invocation_event(
    *,
    run_id: str,
    event_id: str,
    actor: str,
    system: str,
    tool_name: str,
    tool_input_digest: str,
    extra_payload: Mapping[str, Any] | None = None,
) -> EvidenceEvent:
    """Construct a documentation-friendly evidence event for a tool call."""
    payload: dict[str, Any] = {
        "tool_name": tool_name,
        "tool_input_digest": tool_input_digest,
    }
    if extra_payload:
        payload.update(dict(extra_payload))
    return EvidenceEvent(
        event_id=event_id,
        event_type="tool_invoked",
        ts_utc=utc_ts(),
        actor=actor,
        system=system,
        run_id=run_id,
        payload=payload,
    )


def make_tool_evidence_hook(
    submit: Callable[[EvidenceEvent], Any],
    *,
    run_id: str,
    actor: str,
    system: str,
    event_id_for: Callable[[str, str], str] | None = None,
) -> Callable[[str, str], None]:
    """Return ``on_tool(tool_name, input_digest)`` for use inside LangChain callbacks."""

    def _default_eid(tool_name: str, digest: str) -> str:
        return f"tool_{tool_name}_{digest[:16]}_{utc_ts()}"

    eid = event_id_for or _default_eid

    def _on_tool(tool_name: str, input_digest: str) -> None:
        ev = build_tool_invocation_event(
            run_id=run_id,
            event_id=eid(tool_name, input_digest),
            actor=actor,
            system=system,
            tool_name=tool_name,
            tool_input_digest=input_digest,
        )
        submit(ev)

    return _on_tool
