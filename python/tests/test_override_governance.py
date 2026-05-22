from __future__ import annotations

from datetime import datetime, timezone

from aigov_py.overrides import (
    OverrideDecision,
    OverrideRequest,
    OverrideStatus,
    evaluate_override_decision,
    validate_override_request,
)


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc)


def _base_expires() -> datetime:
    return _utc(datetime(2030, 1, 2, 12, 0, 0))


def test_valid_request_passes() -> None:
    req = OverrideRequest(
        requester_id="alice",
        justification="documented exception for pilot",
        expires_at=_base_expires(),
        target_decision_id="dec-1",
    )
    assert validate_override_request(req) == ()


def test_missing_justification_fails() -> None:
    req = OverrideRequest(
        requester_id="alice",
        justification="   ",
        expires_at=_base_expires(),
        target_control_id="ctl-1",
    )
    errs = validate_override_request(req)
    assert errs
    assert "justification is required and must be non-empty" in errs


def test_missing_target_fails() -> None:
    req = OverrideRequest(
        requester_id="alice",
        justification="ok",
        expires_at=_base_expires(),
        target_decision_id=None,
        target_control_id="  ",
    )
    errs = validate_override_request(req)
    assert errs
    assert "target decision or control reference is required" in errs


def test_missing_expiration_fails() -> None:
    req = OverrideRequest(
        requester_id="alice",
        justification="ok",
        expires_at=None,
        target_decision_id="dec-1",
    )
    errs = validate_override_request(req)
    assert errs
    assert "expiration is required" in errs


def test_requester_cannot_approve_own_override() -> None:
    exp = _base_expires()
    req = OverrideRequest(
        requester_id="alice",
        justification="needs human break-glass",
        expires_at=exp,
        target_decision_id="dec-9",
    )
    dec = OverrideDecision(request=req, status=OverrideStatus.REQUESTED)
    now = _utc(datetime(2029, 6, 1, 0, 0, 0))
    out, errs = evaluate_override_decision(
        decision=dec,
        action="approve",
        actor_id="alice",
        now=now,
    )
    assert errs
    assert out is dec
    assert "approver cannot equal requester" in errs


def test_expired_override_cannot_approve() -> None:
    exp = _utc(datetime(2020, 1, 1, 0, 0, 0))
    req = OverrideRequest(
        requester_id="alice",
        justification="was valid once",
        expires_at=exp,
        target_control_id="ctl-2",
    )
    dec = OverrideDecision(request=req, status=OverrideStatus.REQUESTED)
    now = _utc(datetime(2021, 1, 1, 0, 0, 0))
    out, errs = evaluate_override_decision(
        decision=dec,
        action="approve",
        actor_id="bob",
        now=now,
    )
    assert errs
    assert out is dec
    assert "expired override cannot be approved" in errs


def test_revoke_without_reason_fails() -> None:
    exp = _base_expires()
    req = OverrideRequest(
        requester_id="alice",
        justification="pilot",
        expires_at=exp,
        target_decision_id="dec-3",
    )
    dec = OverrideDecision(request=req, status=OverrideStatus.APPROVED)
    now = _utc(datetime(2029, 7, 1, 0, 0, 0))
    out, errs = evaluate_override_decision(
        decision=dec,
        action="revoke",
        actor_id="bob",
        now=now,
        revoke_reason="  ",
    )
    assert errs
    assert out is dec
    assert "revoke requires a non-empty reason" in errs


def test_rejected_override_remains_rejected() -> None:
    exp = _base_expires()
    req = OverrideRequest(
        requester_id="alice",
        justification="try again",
        expires_at=exp,
        target_decision_id="dec-4",
    )
    dec = OverrideDecision(request=req, status=OverrideStatus.REJECTED)
    now = _utc(datetime(2029, 7, 1, 0, 0, 0))
    out, errs = evaluate_override_decision(
        decision=dec,
        action="approve",
        actor_id="bob",
        now=now,
    )
    assert errs
    assert out is dec
    assert "rejected override remains rejected" in errs


def test_deterministic_repeated_evaluation() -> None:
    exp = _base_expires()
    req = OverrideRequest(
        requester_id="alice",
        justification="governed",
        expires_at=exp,
        target_decision_id="dec-5",
    )
    dec = OverrideDecision(request=req, status=OverrideStatus.REQUESTED)
    now = _utc(datetime(2029, 7, 1, 0, 0, 0))
    a = evaluate_override_decision(decision=dec, action="approve", actor_id="bob", now=now)
    b = evaluate_override_decision(decision=dec, action="approve", actor_id="bob", now=now)
    assert a == b
    assert a[1] == ()
    assert a[0].status is OverrideStatus.APPROVED


def test_unknown_action_fails_safely() -> None:
    exp = _base_expires()
    req = OverrideRequest(
        requester_id="alice",
        justification="x",
        expires_at=exp,
        target_control_id="c1",
    )
    dec = OverrideDecision(request=req, status=OverrideStatus.REQUESTED)
    out, errs = evaluate_override_decision(
        decision=dec,
        action="not_a_real_action",
        actor_id="bob",
        now=_utc(datetime(2029, 1, 1, 0, 0, 0)),
    )
    assert out is dec
    assert errs == ("unknown action",)
