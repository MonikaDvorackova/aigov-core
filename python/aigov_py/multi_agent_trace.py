"""
Phase 4 M4 — multi-agent trace **export planning** helpers.

Pure functions only: deterministic ordering, per-event digest chain, and trace digest.
No runtime enforcement, persistence, network, file I/O, or ledger writes.

Refs-only surfaces (identifiers, digests, correlation ids) — no prompts, raw payloads,
or dataset content fields are modeled here.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from aigov_py.canonical_json import canonical_bytes
from aigov_py.runtime_governance import RuntimeGovernanceContext

MULTI_AGENT_TRACE_SCHEMA_VERSION = "aigov.multi_agent_trace.v1"

_DIGEST_ALG = "sha256"

_ERR_TENANT_ID = "tenant_id is required and must be non-empty"
_ERR_TRACE_ID = "trace_id is required and must be non-empty"
_ERR_POLICY_SNAPSHOT = (
    "policy_snapshot_id is required and must be non-empty"
)
_ERR_EVENT_ID = "each event needs a non-empty event_id"
_ERR_SEQUENCE = "sequence_number must be an int >= 0"


def _strip(s: str | None) -> str:
    return (s or "").strip()


def _digest_hex(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(dict(payload))).hexdigest()


@dataclass(frozen=True)
class AgentTraceRef:
    """Opaque identity refs for an acting agent step (no raw content)."""

    agent_id: str | None = None
    principal_id: str | None = None

    def __post_init__(self) -> None:
        if self.agent_id is not None and not _strip(self.agent_id):
            raise ValueError("agent_id, if set, must be non-empty after strip")
        if self.principal_id is not None and not _strip(self.principal_id):
            raise ValueError(
                "principal_id, if set, must be non-empty after strip"
            )


@dataclass(frozen=True)
class DelegationTraceRef:
    """Delegation edge refs only (M2-aligned strings; no graph persistence)."""

    delegation_id: str
    parent_delegation_id: str | None = None
    delegator_agent_id: str | None = None
    delegatee_agent_id: str | None = None
    delegated_capability_id: str | None = None

    def __post_init__(self) -> None:
        if not _strip(self.delegation_id):
            raise ValueError("delegation_id is required and must be non-empty")
        for name, val in (
            ("parent_delegation_id", self.parent_delegation_id),
            ("delegator_agent_id", self.delegator_agent_id),
            ("delegatee_agent_id", self.delegatee_agent_id),
            ("delegated_capability_id", self.delegated_capability_id),
        ):
            if val is not None and not _strip(val):
                raise ValueError(f"{name}, if set, must be non-empty after strip")


@dataclass(frozen=True)
class CapabilityTraceRef:
    capability_id: str
    capability_digest: str | None = None

    def __post_init__(self) -> None:
        if not _strip(self.capability_id):
            raise ValueError("capability_id is required and must be non-empty")
        if self.capability_digest is not None and not _strip(
            self.capability_digest
        ):
            raise ValueError(
                "capability_digest, if set, must be non-empty after strip"
            )


@dataclass(frozen=True)
class MultiAgentTraceEvent:
    """
    One ordered step in a trace. Digests may be omitted at construction time;
    :func:`build_multi_agent_trace` fills ``previous_event_digest`` and ``event_digest``.
    """

    event_id: str
    sequence_number: int
    decision_id: str | None = None
    correlation_id: str | None = None
    agent_context: AgentTraceRef | None = None
    delegation_context: DelegationTraceRef | None = None
    capability_refs: tuple[CapabilityTraceRef, ...] = ()
    previous_event_digest: str | None = None
    event_digest: str | None = None

    def __post_init__(self) -> None:
        if not _strip(self.event_id):
            raise ValueError(_ERR_EVENT_ID)
        if not isinstance(self.sequence_number, int) or self.sequence_number < 0:
            raise ValueError(_ERR_SEQUENCE)


@dataclass(frozen=True)
class MultiAgentTrace:
    trace_schema_version: str
    tenant_id: str
    trace_id: str
    policy_snapshot_id: str
    events: tuple[MultiAgentTraceEvent, ...]
    trace_digest: str

    def __post_init__(self) -> None:
        if not _strip(self.tenant_id):
            raise ValueError(_ERR_TENANT_ID)
        if not _strip(self.trace_id):
            raise ValueError(_ERR_TRACE_ID)
        if not _strip(self.policy_snapshot_id):
            raise ValueError(_ERR_POLICY_SNAPSHOT)


@dataclass(frozen=True)
class TraceDigestSummary:
    """Digest metadata for exported trace planning artifacts."""

    digest_algorithm: str
    trace_schema_version: str
    trace_digest: str
    event_count: int


def _sorted_capability_refs(
    refs: Iterable[CapabilityTraceRef],
) -> tuple[CapabilityTraceRef, ...]:
    lst = list(refs)
    lst.sort(
        key=lambda r: (
            _strip(r.capability_id),
            _strip(r.capability_digest or ""),
        )
    )
    return tuple(lst)


def _agent_ref_dict(ref: AgentTraceRef) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if ref.agent_id is not None:
        out["agent_id"] = _strip(ref.agent_id)
    if ref.principal_id is not None:
        out["principal_id"] = _strip(ref.principal_id)
    return dict(sorted(out.items()))


def _delegation_ref_dict(ref: DelegationTraceRef) -> dict[str, Any]:
    d: dict[str, Any] = {"delegation_id": _strip(ref.delegation_id)}
    if ref.parent_delegation_id is not None:
        d["parent_delegation_id"] = _strip(ref.parent_delegation_id)
    if ref.delegator_agent_id is not None:
        d["delegator_agent_id"] = _strip(ref.delegator_agent_id)
    if ref.delegatee_agent_id is not None:
        d["delegatee_agent_id"] = _strip(ref.delegatee_agent_id)
    if ref.delegated_capability_id is not None:
        d["delegated_capability_id"] = _strip(ref.delegated_capability_id)
    return dict(sorted(d.items()))


def _capability_ref_dict(ref: CapabilityTraceRef) -> dict[str, Any]:
    d: dict[str, Any] = {"capability_id": _strip(ref.capability_id)}
    if ref.capability_digest is not None:
        d["capability_digest"] = _strip(ref.capability_digest)
    return dict(sorted(d.items()))


def _event_body_for_event_digest(ev: MultiAgentTraceEvent) -> dict[str, Any]:
    """Canonical event payload for a single event_digest (excludes event_digest only)."""
    cap = [_capability_ref_dict(r) for r in _sorted_capability_refs(ev.capability_refs)]
    parts: dict[str, Any] = {
        "capability_refs": cap,
        "event_id": _strip(ev.event_id),
        "previous_event_digest": ev.previous_event_digest or "",
        "sequence_number": ev.sequence_number,
    }
    if ev.correlation_id is not None and _strip(ev.correlation_id):
        parts["correlation_id"] = _strip(ev.correlation_id)
    if ev.decision_id is not None and _strip(ev.decision_id):
        parts["decision_id"] = _strip(ev.decision_id)
    if ev.agent_context is not None:
        parts["agent_context"] = _agent_ref_dict(ev.agent_context)
    if ev.delegation_context is not None:
        parts["delegation_context"] = _delegation_ref_dict(ev.delegation_context)
    return dict(sorted(parts.items()))


def _finalize_event_digests(
    ordered: Sequence[MultiAgentTraceEvent],
) -> tuple[MultiAgentTraceEvent, ...]:
    out: list[MultiAgentTraceEvent] = []
    prev_chain = ""
    for ev in ordered:
        body = _event_body_for_event_digest(
            MultiAgentTraceEvent(
                event_id=ev.event_id,
                sequence_number=ev.sequence_number,
                decision_id=ev.decision_id,
                correlation_id=ev.correlation_id,
                agent_context=ev.agent_context,
                delegation_context=ev.delegation_context,
                capability_refs=ev.capability_refs,
                previous_event_digest=prev_chain,
                event_digest=None,
            )
        )
        ed = _digest_hex(body)
        finalized = MultiAgentTraceEvent(
            event_id=ev.event_id,
            sequence_number=ev.sequence_number,
            decision_id=ev.decision_id,
            correlation_id=ev.correlation_id,
            agent_context=ev.agent_context,
            delegation_context=ev.delegation_context,
            capability_refs=ev.capability_refs,
            previous_event_digest=prev_chain if prev_chain else None,
            event_digest=ed,
        )
        out.append(finalized)
        prev_chain = ed
    return tuple(out)


def _event_export_dict(ev: MultiAgentTraceEvent) -> dict[str, Any]:
    cap = [_capability_ref_dict(r) for r in _sorted_capability_refs(ev.capability_refs)]
    parts: dict[str, Any] = {
        "capability_refs": cap,
        "event_digest": ev.event_digest,
        "event_id": _strip(ev.event_id),
        "previous_event_digest": (ev.previous_event_digest or ""),
        "sequence_number": ev.sequence_number,
    }
    if ev.correlation_id is not None and _strip(ev.correlation_id):
        parts["correlation_id"] = _strip(ev.correlation_id)
    if ev.decision_id is not None and _strip(ev.decision_id):
        parts["decision_id"] = _strip(ev.decision_id)
    if ev.agent_context is not None:
        parts["agent_context"] = _agent_ref_dict(ev.agent_context)
    if ev.delegation_context is not None:
        parts["delegation_context"] = _delegation_ref_dict(ev.delegation_context)
    return dict(sorted(parts.items()))


def trace_digest_preimage(trace: MultiAgentTrace) -> dict[str, Any]:
    """
    Canonical payload hashed for ``trace_digest`` (excludes only top-level ``trace_digest``).
    """
    ev_maps = [_event_export_dict(e) for e in trace.events]
    payload = {
        "events": ev_maps,
        "policy_snapshot_id": _strip(trace.policy_snapshot_id),
        "tenant_id": _strip(trace.tenant_id),
        "trace_id": _strip(trace.trace_id),
        "trace_schema_version": _strip(trace.trace_schema_version),
    }
    return dict(sorted(payload.items()))


def compute_trace_digest(trace: MultiAgentTrace) -> str:
    """SHA-256 hex over :func:`trace_digest_preimage` (same as stored ``trace_digest``)."""
    return _digest_hex(trace_digest_preimage(trace))


def validate_multi_agent_trace_provenance(
    *,
    tenant_id: str,
    trace_id: str,
    policy_snapshot_id: str,
) -> tuple[str, ...]:
    errors: list[str] = []
    if not _strip(tenant_id):
        errors.append(_ERR_TENANT_ID)
    if not _strip(trace_id):
        errors.append(_ERR_TRACE_ID)
    if not _strip(policy_snapshot_id):
        errors.append(_ERR_POLICY_SNAPSHOT)
    return tuple(sorted(frozenset(errors)))


def order_events(
    events: Sequence[MultiAgentTraceEvent],
) -> tuple[MultiAgentTraceEvent, ...]:
    """Deterministic ordering: ``sequence_number`` ascending, then ``event_id``."""
    lst = list(events)
    lst.sort(key=lambda e: (e.sequence_number, _strip(e.event_id)))
    return tuple(lst)


def build_multi_agent_trace(
    *,
    trace_schema_version: str = MULTI_AGENT_TRACE_SCHEMA_VERSION,
    tenant_id: str,
    trace_id: str,
    policy_snapshot_id: str,
    events: Sequence[MultiAgentTraceEvent],
) -> tuple[MultiAgentTrace, TraceDigestSummary]:
    """
    Validate provenance fields, order events, compute per-event digest chain and trace digest.
    """
    errs = validate_multi_agent_trace_provenance(
        tenant_id=tenant_id,
        trace_id=trace_id,
        policy_snapshot_id=policy_snapshot_id,
    )
    if errs:
        raise ValueError("; ".join(errs))

    ordered = order_events(events)
    finalized_events = _finalize_event_digests(ordered)

    trace = MultiAgentTrace(
        trace_schema_version=_strip(trace_schema_version),
        tenant_id=_strip(tenant_id),
        trace_id=_strip(trace_id),
        policy_snapshot_id=_strip(policy_snapshot_id),
        events=finalized_events,
        trace_digest="",
    )
    td = compute_trace_digest(
        MultiAgentTrace(
            trace_schema_version=trace.trace_schema_version,
            tenant_id=trace.tenant_id,
            trace_id=trace.trace_id,
            policy_snapshot_id=trace.policy_snapshot_id,
            events=trace.events,
            trace_digest="",
        )
    )
    trace = MultiAgentTrace(
        trace_schema_version=trace.trace_schema_version,
        tenant_id=trace.tenant_id,
        trace_id=trace.trace_id,
        policy_snapshot_id=trace.policy_snapshot_id,
        events=trace.events,
        trace_digest=td,
    )
    summary = TraceDigestSummary(
        digest_algorithm=_DIGEST_ALG,
        trace_schema_version=trace.trace_schema_version,
        trace_digest=td,
        event_count=len(finalized_events),
    )
    return trace, summary


def trace_event_from_runtime_governance_context(
    *,
    event_id: str,
    sequence_number: int,
    ctx: RuntimeGovernanceContext,
    agent_context: AgentTraceRef | None = None,
    delegation_context: DelegationTraceRef | None = None,
    capability_refs: tuple[CapabilityTraceRef, ...] = (),
) -> MultiAgentTraceEvent:
    """
    Map a :class:`RuntimeGovernanceContext` to a trace event shell (refs only).

    Uses ``runtime_decision_id`` / ``correlation_id``; does not embed lineage payloads.
    """
    return MultiAgentTraceEvent(
        event_id=event_id,
        sequence_number=sequence_number,
        decision_id=_strip(ctx.runtime_decision_id) or None,
        correlation_id=_strip(ctx.correlation_id) or None,
        agent_context=agent_context,
        delegation_context=delegation_context,
        capability_refs=capability_refs,
    )
