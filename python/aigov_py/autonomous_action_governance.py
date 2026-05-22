"""Autonomous action governance: autonomy levels, policy, deterministic evaluation (stdlib).

The canonical runtime enforcement path for hosted deployments is the Rust audit service
(`GOVAI_AUTONOMY_ENFORCEMENT` + `govai_tenant_autonomy_policy` + POST /evidence gate), aligned with
these rules. This module remains the portable reference implementation for planning and tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AutonomyLevel(Enum):
    """Ordinal autonomy scale; higher values imply stronger safeguards when autonomous."""

    LEVEL_0_MANUAL = 0
    LEVEL_1_ASSISTED = 1
    LEVEL_2_SUPERVISED = 2
    LEVEL_3_CONDITIONAL_AUTONOMY = 3
    LEVEL_4_HIGH_AUTONOMY = 4
    LEVEL_5_FULL_AUTONOMY = 5


class StopControlState(Enum):
    """Emergency stop / tenant stop control posture (planning)."""

    OPERATIONAL = "OPERATIONAL"
    EMERGENCY_STOP_ACTIVE = "EMERGENCY_STOP_ACTIVE"


class KillSwitchState(Enum):
    """Platform or global kill-switch posture (planning)."""

    NOT_ENGAGED = "NOT_ENGAGED"
    ENGAGED = "ENGAGED"


class HumanCheckpointRequirement(Enum):
    """What human checkpoint applies for the attempted action (metadata only)."""

    NONE = "NONE"
    HUMAN_EXECUTION_REQUIRED = "HUMAN_EXECUTION_REQUIRED"
    PRE_AUTONOMOUS_APPROVAL = "PRE_AUTONOMOUS_APPROVAL"
    DUAL_APPROVAL_CHECKPOINT = "DUAL_APPROVAL_CHECKPOINT"
    POST_ACTION_REVIEW = "POST_ACTION_REVIEW"


@dataclass(frozen=True)
class AutonomousActionPolicy:
    """Tenant-scoped policy slice for autonomous capability execution (planning schema)."""

    policy_id: str
    tenant_id: str
    autonomy_level: AutonomyLevel
    allowed_capabilities: frozenset[str]
    required_human_roles: tuple[str, ...]
    requires_approval: bool
    requires_dual_approval: bool
    requires_override_reference: bool
    stop_controls_enabled: bool
    kill_switch_enabled: bool


@dataclass(frozen=True)
class AutonomousActionDecision:
    """Deterministic planning outcome for one capability request under a policy."""

    permitted: bool
    blocked_reason_codes: tuple[str, ...]
    required_approvals: tuple[str, ...]
    required_override: bool
    required_stop_controls: bool
    accountability_requirements: tuple[str, ...]


_REASON_CAPABILITY_NOT_ALLOWED = "CAPABILITY_NOT_ALLOWED"
_REASON_EMPTY_CAPABILITY = "EMPTY_CAPABILITY_ID"
_REASON_LEVEL_0_MANUAL = "LEVEL_0_REQUIRES_HUMAN_ACTION"
_REASON_POLICY_STOP_CONTROLS = "POLICY_STOP_CONTROLS_REQUIRED_FOR_LEVEL"
_REASON_POLICY_KILL_SWITCH = "POLICY_KILL_SWITCH_REQUIRED_FOR_LEVEL"
_REASON_POLICY_LEVEL_5 = "POLICY_LEVEL_5_REQUIRES_DUAL_APPROVAL_AND_OVERRIDE"
_REASON_EMERGENCY_STOP = "EMERGENCY_STOP_ACTIVE"
_REASON_KILL_SWITCH = "KILL_SWITCH_ENGAGED"

_ACCT_AUDIT = "AUDIT_TRACE_REQUIRED"
_ACCT_AGENT_ATTRIBUTION = "AGENT_ATTRIBUTION_REQUIRED"
_ACCT_APPROVAL_RECORD = "HUMAN_APPROVAL_RECORD_REQUIRED"
_ACCT_DUAL_APPROVAL = "DUAL_APPROVAL_RECORD_REQUIRED"
_ACCT_OVERRIDE_REF = "EXPLICIT_OVERRIDE_REFERENCE_REQUIRED"
_ACCT_STOP_CONTROLS = "STOP_CONTROL_GOVERNANCE_REQUIRED"
_ACCT_KILL_SWITCH = "KILL_SWITCH_GOVERNANCE_REQUIRED"


def _norm_cap(s: str) -> str:
    return (s or "").strip()


def _sorted_codes(codes: frozenset[str]) -> tuple[str, ...]:
    return tuple(sorted(codes))


def _role_requirement_tokens(roles: tuple[str, ...]) -> tuple[str, ...]:
    out: list[str] = []
    for r in sorted({x.strip() for x in roles if x.strip()}):
        out.append(f"HUMAN_ROLE:{r}")
    return tuple(out)


def evaluate_autonomous_action(
    policy: AutonomousActionPolicy,
    requested_capability_id: str,
    *,
    stop_control_state: StopControlState = StopControlState.OPERATIONAL,
    kill_switch_state: KillSwitchState = KillSwitchState.NOT_ENGAGED,
) -> AutonomousActionDecision:
    """Return a deterministic governance planning decision (no side effects).

    Rules (summary):
    - Missing or non-allowed capability blocks.
    - LEVEL_0 blocks autonomous execution (human must perform the action).
    - LEVEL_3+ requires policy stop-controls enabled; operational stop state required.
    - LEVEL_4+ requires policy kill-switch enabled; kill-switch must not be engaged.
    - LEVEL_5 requires dual approval and override reference on the policy.
    - Higher autonomy implies stricter structural checks on policy and controls.
    """
    cap = _norm_cap(requested_capability_id)
    blocked: set[str] = set()

    if not cap:
        blocked.add(_REASON_EMPTY_CAPABILITY)

    if cap and cap not in policy.allowed_capabilities:
        blocked.add(_REASON_CAPABILITY_NOT_ALLOWED)

    level = policy.autonomy_level

    if level == AutonomyLevel.LEVEL_0_MANUAL:
        blocked.add(_REASON_LEVEL_0_MANUAL)

    if level.value >= AutonomyLevel.LEVEL_3_CONDITIONAL_AUTONOMY.value:
        if not policy.stop_controls_enabled:
            blocked.add(_REASON_POLICY_STOP_CONTROLS)
        if stop_control_state == StopControlState.EMERGENCY_STOP_ACTIVE:
            blocked.add(_REASON_EMERGENCY_STOP)

    if level.value >= AutonomyLevel.LEVEL_4_HIGH_AUTONOMY.value:
        if not policy.kill_switch_enabled:
            blocked.add(_REASON_POLICY_KILL_SWITCH)
        if kill_switch_state == KillSwitchState.ENGAGED:
            blocked.add(_REASON_KILL_SWITCH)

    if level == AutonomyLevel.LEVEL_5_FULL_AUTONOMY:
        if not (policy.requires_dual_approval and policy.requires_override_reference):
            blocked.add(_REASON_POLICY_LEVEL_5)

    permitted = len(blocked) == 0

    required_stop = level.value >= AutonomyLevel.LEVEL_3_CONDITIONAL_AUTONOMY.value
    required_override = level.value >= AutonomyLevel.LEVEL_5_FULL_AUTONOMY.value or (
        policy.requires_override_reference
    )

    approvals: list[str] = []
    if level.value >= AutonomyLevel.LEVEL_1_ASSISTED.value:
        approvals.extend(_role_requirement_tokens(policy.required_human_roles))
    if policy.requires_approval:
        approvals.append("APPROVAL_REQUIRED")
    if policy.requires_dual_approval or level == AutonomyLevel.LEVEL_5_FULL_AUTONOMY:
        approvals.append("DUAL_APPROVAL_REQUIRED")

    accountability: list[str] = [_ACCT_AUDIT, _ACCT_AGENT_ATTRIBUTION]
    if level.value >= AutonomyLevel.LEVEL_1_ASSISTED.value and (
        policy.requires_approval or policy.required_human_roles
    ):
        accountability.append(_ACCT_APPROVAL_RECORD)
    if policy.requires_dual_approval or level == AutonomyLevel.LEVEL_5_FULL_AUTONOMY:
        accountability.append(_ACCT_DUAL_APPROVAL)
    if required_override:
        accountability.append(_ACCT_OVERRIDE_REF)
    if required_stop:
        accountability.append(_ACCT_STOP_CONTROLS)
    if level.value >= AutonomyLevel.LEVEL_4_HIGH_AUTONOMY.value:
        accountability.append(_ACCT_KILL_SWITCH)

    required_approvals = tuple(sorted(set(approvals)))
    accountability_requirements = tuple(sorted(set(accountability)))

    return AutonomousActionDecision(
        permitted=permitted,
        blocked_reason_codes=_sorted_codes(frozenset(blocked)),
        required_approvals=required_approvals,
        required_override=required_override,
        required_stop_controls=required_stop,
        accountability_requirements=accountability_requirements,
    )


def human_checkpoint_for_decision(
    policy: AutonomousActionPolicy,
    decision: AutonomousActionDecision,
) -> HumanCheckpointRequirement:
    """Derive a single checkpoint label from policy level and decision (deterministic)."""
    if policy.autonomy_level == AutonomyLevel.LEVEL_0_MANUAL:
        return HumanCheckpointRequirement.HUMAN_EXECUTION_REQUIRED
    if not decision.permitted:
        return HumanCheckpointRequirement.PRE_AUTONOMOUS_APPROVAL
    if policy.requires_dual_approval or policy.autonomy_level == AutonomyLevel.LEVEL_5_FULL_AUTONOMY:
        return HumanCheckpointRequirement.DUAL_APPROVAL_CHECKPOINT
    if policy.requires_approval:
        return HumanCheckpointRequirement.PRE_AUTONOMOUS_APPROVAL
    if policy.autonomy_level.value >= AutonomyLevel.LEVEL_2_SUPERVISED.value:
        return HumanCheckpointRequirement.POST_ACTION_REVIEW
    return HumanCheckpointRequirement.NONE
