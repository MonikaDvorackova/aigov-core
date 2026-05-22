from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class OverrideStatus(Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass(frozen=True)
class OverrideRequest:
    """Human override request metadata (governance primitive; not enforced at runtime)."""

    requester_id: str
    justification: str
    expires_at: datetime | None
    target_decision_id: str | None = None
    target_control_id: str | None = None


@dataclass(frozen=True)
class OverrideDecision:
    """Lifecycle snapshot for an override: validated request plus current status."""

    request: OverrideRequest
    status: OverrideStatus


_ERR_ACTOR_REQUIRED = "actor_id is required and must be non-empty"
_ERR_REQUESTER_REQUIRED = "requester_id is required and must be non-empty"
_ERR_APPROVER_CANNOT_EQUAL_REQUESTER = "approver cannot equal requester"
_ERR_CANNOT_APPROVE_EXPIRED_OVERRIDE = "expired override cannot be approved"
_ERR_INVALID_STATUS_FOR_ACTION = "invalid status for this action"
_ERR_JUSTIFICATION_REQUIRED = "justification is required and must be non-empty"
_ERR_REJECTED_OVERRIDE_REMAINS_REJECTED = "rejected override remains rejected"
_ERR_REVOKE_REQUIRES_APPROVED_OVERRIDE = "revoke is only valid for an approved override"
_ERR_REVOKE_REQUIRES_REASON = "revoke requires a non-empty reason"
_ERR_TARGET_REFERENCE_REQUIRED = "target decision or control reference is required"
_ERR_EXPIRATION_REQUIRED = "expiration is required"
_ERR_UNKNOWN_ACTION = "unknown action"


def validate_override_request(request: OverrideRequest) -> tuple[str, ...]:
    """Return sorted, deterministic error messages; empty tuple means valid."""
    errors: list[str] = []

    if not (request.requester_id or "").strip():
        errors.append(_ERR_REQUESTER_REQUIRED)
    tgt_dec = (request.target_decision_id or "").strip()
    tgt_ctl = (request.target_control_id or "").strip()
    if not tgt_dec and not tgt_ctl:
        errors.append(_ERR_TARGET_REFERENCE_REQUIRED)
    if not (request.justification or "").strip():
        errors.append(_ERR_JUSTIFICATION_REQUIRED)
    if request.expires_at is None:
        errors.append(_ERR_EXPIRATION_REQUIRED)

    return tuple(sorted(errors))


def _parse_action(action: str) -> str | None:
    a = (action or "").strip().lower()
    if a in {"approve", "reject", "revoke"}:
        return a
    return None


def evaluate_override_decision(
    *,
    decision: OverrideDecision,
    action: str,
    actor_id: str,
    now: datetime,
    revoke_reason: str | None = None,
) -> tuple[OverrideDecision, tuple[str, ...]]:
    """
    Apply a governance lifecycle action with default-safe rules.

    On failure, returns the original ``decision`` unchanged and a non-empty sorted error tuple.
    On success, returns a new ``OverrideDecision`` with updated status and empty errors.
    """
    errs = validate_override_request(decision.request)
    if errs:
        return decision, errs

    act = _parse_action(action)
    if act is None:
        return decision, (_ERR_UNKNOWN_ACTION,)

    if not (actor_id or "").strip():
        return decision, (_ERR_ACTOR_REQUIRED,)

    st = decision.status

    if act == "approve":
        if st is OverrideStatus.REJECTED:
            return decision, (_ERR_REJECTED_OVERRIDE_REMAINS_REJECTED,)
        if st is not OverrideStatus.REQUESTED:
            return decision, (_ERR_INVALID_STATUS_FOR_ACTION,)
        exp_at = decision.request.expires_at
        if exp_at is None:
            return decision, (_ERR_EXPIRATION_REQUIRED,)
        if now >= exp_at:
            return decision, (_ERR_CANNOT_APPROVE_EXPIRED_OVERRIDE,)
        if actor_id.strip() == decision.request.requester_id.strip():
            return decision, (_ERR_APPROVER_CANNOT_EQUAL_REQUESTER,)
        return OverrideDecision(request=decision.request, status=OverrideStatus.APPROVED), ()

    if act == "reject":
        if st is OverrideStatus.REJECTED:
            return decision, (_ERR_REJECTED_OVERRIDE_REMAINS_REJECTED,)
        if st is not OverrideStatus.REQUESTED:
            return decision, (_ERR_INVALID_STATUS_FOR_ACTION,)
        return OverrideDecision(request=decision.request, status=OverrideStatus.REJECTED), ()

    if act == "revoke":
        if st is not OverrideStatus.APPROVED:
            return decision, (_ERR_REVOKE_REQUIRES_APPROVED_OVERRIDE,)
        if not (revoke_reason or "").strip():
            return decision, (_ERR_REVOKE_REQUIRES_REASON,)
        return OverrideDecision(request=decision.request, status=OverrideStatus.REVOKED), ()

    return decision, (_ERR_UNKNOWN_ACTION,)
