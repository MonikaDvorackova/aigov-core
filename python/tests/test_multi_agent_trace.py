from __future__ import annotations

import dataclasses

import pytest

from aigov_py.multi_agent_trace import (
    MULTI_AGENT_TRACE_SCHEMA_VERSION,
    AgentTraceRef,
    CapabilityTraceRef,
    DelegationTraceRef,
    MultiAgentTraceEvent,
    build_multi_agent_trace,
    compute_trace_digest,
    order_events,
    trace_digest_preimage,
    trace_event_from_runtime_governance_context,
)
from aigov_py.runtime_governance import (
    RuntimeControlEvaluation,
    RuntimeControlStatus,
    RuntimeGovernanceContext,
    RuntimeGovernanceVerdict,
    RuntimeRiskClass,
    summarize_runtime_governance,
)


def _minimal_ctx(*, decision_id: str = "d1", correlation_id: str = "c1") -> RuntimeGovernanceContext:
    return RuntimeGovernanceContext(
        runtime_decision_id=decision_id,
        correlation_id=correlation_id,
        tenant_id="t1",
        artifact_digest="a" * 64,
        policy_bundle_version="pv1",
        risk_class=RuntimeRiskClass.MINIMAL,
        control_evaluations=(
            RuntimeControlEvaluation(
                "ctl1", RuntimeControlStatus.PASS, (), ()
            ),
        ),
    )


def test_valid_trace_builds() -> None:
    ev1 = MultiAgentTraceEvent(
        event_id="e1",
        sequence_number=1,
        decision_id="d1",
        correlation_id="c1",
    )
    trace, summary = build_multi_agent_trace(
        tenant_id="tenant-a",
        trace_id="trace-a",
        policy_snapshot_id="snap-1",
        events=(ev1,),
    )
    assert trace.tenant_id == "tenant-a"
    assert trace.trace_id == "trace-a"
    assert trace.policy_snapshot_id == "snap-1"
    assert len(trace.events) == 1
    assert trace.events[0].event_digest
    assert compute_trace_digest(trace) == trace.trace_digest
    assert summary.trace_digest == trace.trace_digest
    assert summary.event_count == 1
    assert summary.digest_algorithm == "sha256"
    assert summary.trace_schema_version == MULTI_AGENT_TRACE_SCHEMA_VERSION


def test_missing_tenant_id_fails_validation() -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        build_multi_agent_trace(
            tenant_id="",
            trace_id="x",
            policy_snapshot_id="p",
            events=(
                MultiAgentTraceEvent(event_id="e", sequence_number=0),
            ),
        )


def test_missing_trace_id_fails_validation() -> None:
    with pytest.raises(ValueError, match="trace_id"):
        build_multi_agent_trace(
            tenant_id="t",
            trace_id="  ",
            policy_snapshot_id="p",
            events=(MultiAgentTraceEvent(event_id="e", sequence_number=0),),
        )


def test_missing_policy_snapshot_id_fails_validation() -> None:
    with pytest.raises(ValueError, match="policy_snapshot_id"):
        build_multi_agent_trace(
            tenant_id="t",
            trace_id="tr",
            policy_snapshot_id="",
            events=(MultiAgentTraceEvent(event_id="e", sequence_number=0),),
        )


def test_deterministic_digest_stable() -> None:
    agent = AgentTraceRef(agent_id="ag1", principal_id="p1")
    delg = DelegationTraceRef(delegation_id="dg1")
    cap = (CapabilityTraceRef(capability_id="cap.a"),)
    ev = MultiAgentTraceEvent(
        event_id="e1",
        sequence_number=0,
        agent_context=agent,
        delegation_context=delg,
        capability_refs=cap,
        decision_id="d1",
        correlation_id="c1",
    )
    t1, _ = build_multi_agent_trace(
        tenant_id="tenant-a",
        trace_id="trace-a",
        policy_snapshot_id="snap-1",
        events=(ev,),
    )
    t2, _ = build_multi_agent_trace(
        tenant_id="tenant-a",
        trace_id="trace-a",
        policy_snapshot_id="snap-1",
        events=(ev,),
    )
    assert t1.trace_digest == t2.trace_digest
    assert t1.events[0].event_digest == t2.events[0].event_digest


def test_changed_event_changes_digest() -> None:
    base = MultiAgentTraceEvent(event_id="e1", sequence_number=0)
    t_a, _ = build_multi_agent_trace(
        tenant_id="t",
        trace_id="tr",
        policy_snapshot_id="p",
        events=(base,),
    )
    changed = MultiAgentTraceEvent(
        event_id="e1",
        sequence_number=0,
        correlation_id="other",
    )
    t_b, _ = build_multi_agent_trace(
        tenant_id="t",
        trace_id="tr",
        policy_snapshot_id="p",
        events=(changed,),
    )
    assert t_a.trace_digest != t_b.trace_digest


def test_ordering_deterministic() -> None:
    a = MultiAgentTraceEvent(event_id="b", sequence_number=1)
    b = MultiAgentTraceEvent(event_id="a", sequence_number=1)
    c = MultiAgentTraceEvent(event_id="z", sequence_number=0)
    ordered = order_events((a, b, c))
    assert [e.event_id for e in ordered] == ["z", "a", "b"]


def test_event_digest_chain_stable() -> None:
    e0 = MultiAgentTraceEvent(event_id="e0", sequence_number=0)
    e1 = MultiAgentTraceEvent(event_id="e1", sequence_number=1)
    trace, _ = build_multi_agent_trace(
        tenant_id="t",
        trace_id="tr",
        policy_snapshot_id="p",
        events=(e1, e0),
    )
    ev0, ev1 = trace.events
    assert ev0.sequence_number == 0
    assert ev1.sequence_number == 1
    assert ev0.previous_event_digest in (None, "")
    assert ev1.previous_event_digest == ev0.event_digest

    t2, _ = build_multi_agent_trace(
        tenant_id="t",
        trace_id="tr",
        policy_snapshot_id="p",
        events=(e0, e1),
    )
    assert [e.event_digest for e in t2.events] == [
        e.event_digest for e in trace.events
    ]
    assert t2.trace_digest == trace.trace_digest


def test_trace_preimage_excludes_trace_digest_field() -> None:
    ev = MultiAgentTraceEvent(event_id="e1", sequence_number=0)
    trace, _ = build_multi_agent_trace(
        tenant_id="t",
        trace_id="tr",
        policy_snapshot_id="p",
        events=(ev,),
    )
    pre = trace_digest_preimage(trace)
    assert "trace_digest" not in pre


def test_raw_content_fields_not_modeled() -> None:
    fields = {f.name for f in dataclasses.fields(MultiAgentTraceEvent)}
    forbidden = (
        "prompt",
        "content",
        "inputs_hash",
        "outputs_hash",
        "dataset_payload",
        "raw",
    )
    for name in forbidden:
        assert name not in fields


def test_refs_only_agent_delegation_capability() -> None:
    agent = AgentTraceRef(agent_id="ag", principal_id="pr")
    delg = DelegationTraceRef(
        delegation_id="d1",
        parent_delegation_id="p0",
        delegator_agent_id="a1",
        delegatee_agent_id="a2",
        delegated_capability_id="cap.x",
    )
    caps = (CapabilityTraceRef(capability_id="c1", capability_digest="abc"),)
    ev = MultiAgentTraceEvent(
        event_id="e1",
        sequence_number=0,
        agent_context=agent,
        delegation_context=delg,
        capability_refs=caps,
    )
    trace, _ = build_multi_agent_trace(
        tenant_id="t",
        trace_id="tr",
        policy_snapshot_id="p",
        events=(ev,),
    )
    fe = trace.events[0]
    assert fe.agent_context == agent
    assert fe.delegation_context == delg
    assert fe.capability_refs == caps


def test_trace_event_from_runtime_governance_context() -> None:
    ctx = _minimal_ctx()
    ge = summarize_runtime_governance(ctx)
    assert ge.verdict == RuntimeGovernanceVerdict.VALID

    ev = trace_event_from_runtime_governance_context(
        event_id="evt1",
        sequence_number=3,
        ctx=ctx,
        agent_context=AgentTraceRef(agent_id="bot"),
        delegation_context=DelegationTraceRef(delegation_id="dg"),
        capability_refs=(CapabilityTraceRef(capability_id="read.email"),),
    )
    assert ev.decision_id == "d1"
    assert ev.correlation_id == "c1"
    trace, _ = build_multi_agent_trace(
        tenant_id="tenant-x",
        trace_id="trace-x",
        policy_snapshot_id="snap-x",
        events=(ev,),
    )
    assert trace.events[0].sequence_number == 3
