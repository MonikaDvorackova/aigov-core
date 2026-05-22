from __future__ import annotations

from aigov_py.autonomous_action_governance import (
    AutonomousActionDecision,
    AutonomousActionPolicy,
    AutonomyLevel,
    KillSwitchState,
    StopControlState,
    evaluate_autonomous_action,
    human_checkpoint_for_decision,
)


def _policy(
    level: AutonomyLevel,
    *,
    caps: frozenset[str] | None = None,
    roles: tuple[str, ...] = (),
    requires_approval: bool = False,
    requires_dual_approval: bool = False,
    requires_override_reference: bool = False,
    stop_controls_enabled: bool = False,
    kill_switch_enabled: bool = False,
) -> AutonomousActionPolicy:
    return AutonomousActionPolicy(
        policy_id="pol-1",
        tenant_id="ten-1",
        autonomy_level=level,
        allowed_capabilities=caps or frozenset({"cap.a"}),
        required_human_roles=roles,
        requires_approval=requires_approval,
        requires_dual_approval=requires_dual_approval,
        requires_override_reference=requires_override_reference,
        stop_controls_enabled=stop_controls_enabled,
        kill_switch_enabled=kill_switch_enabled,
)


def test_each_autonomy_level_maps_required_controls() -> None:
    cap = "cap.a"
    for level in AutonomyLevel:
        stop_on = level.value >= AutonomyLevel.LEVEL_3_CONDITIONAL_AUTONOMY.value
        kill_on = level.value >= AutonomyLevel.LEVEL_4_HIGH_AUTONOMY.value
        pol = _policy(
            level,
            stop_controls_enabled=stop_on,
            kill_switch_enabled=kill_on,
            requires_dual_approval=(level == AutonomyLevel.LEVEL_5_FULL_AUTONOMY),
            requires_override_reference=(level == AutonomyLevel.LEVEL_5_FULL_AUTONOMY),
        )
        dec = evaluate_autonomous_action(
            pol,
            cap,
            stop_control_state=StopControlState.OPERATIONAL,
            kill_switch_state=KillSwitchState.NOT_ENGAGED,
        )
        assert dec.required_stop_controls == stop_on
        if level == AutonomyLevel.LEVEL_0_MANUAL:
            assert dec.permitted is False
            assert "LEVEL_0_REQUIRES_HUMAN_ACTION" in dec.blocked_reason_codes
        elif level == AutonomyLevel.LEVEL_5_FULL_AUTONOMY:
            assert dec.permitted is True
            assert dec.required_override is True
            assert "DUAL_APPROVAL_REQUIRED" in dec.required_approvals
        else:
            assert dec.permitted is True


def test_capability_mismatch_blocks() -> None:
    pol = _policy(AutonomyLevel.LEVEL_2_SUPERVISED)
    dec = evaluate_autonomous_action(pol, "cap.forbidden")
    assert dec.permitted is False
    assert "CAPABILITY_NOT_ALLOWED" in dec.blocked_reason_codes


def test_level_5_requires_dual_approval_and_override_on_policy() -> None:
    pol_bad = _policy(
        AutonomyLevel.LEVEL_5_FULL_AUTONOMY,
        requires_dual_approval=False,
        requires_override_reference=True,
        stop_controls_enabled=True,
        kill_switch_enabled=True,
    )
    assert evaluate_autonomous_action(pol_bad, "cap.a").permitted is False
    pol_bad2 = _policy(
        AutonomyLevel.LEVEL_5_FULL_AUTONOMY,
        requires_dual_approval=True,
        requires_override_reference=False,
        stop_controls_enabled=True,
        kill_switch_enabled=True,
    )
    assert evaluate_autonomous_action(pol_bad2, "cap.a").permitted is False

    pol_ok = _policy(
        AutonomyLevel.LEVEL_5_FULL_AUTONOMY,
        requires_dual_approval=True,
        requires_override_reference=True,
        stop_controls_enabled=True,
        kill_switch_enabled=True,
    )
    dec = evaluate_autonomous_action(pol_ok, "cap.a")
    assert dec.permitted is True
    assert dec.required_override is True
    assert "DUAL_APPROVAL_REQUIRED" in dec.required_approvals


def test_deterministic_output() -> None:
    pol = _policy(
        AutonomyLevel.LEVEL_3_CONDITIONAL_AUTONOMY,
        stop_controls_enabled=True,
    )
    a = evaluate_autonomous_action(
        pol,
        "x",
        stop_control_state=StopControlState.EMERGENCY_STOP_ACTIVE,
    )
    b = evaluate_autonomous_action(
        pol,
        "x",
        stop_control_state=StopControlState.EMERGENCY_STOP_ACTIVE,
    )
    assert a == b
    assert a.blocked_reason_codes == tuple(sorted(a.blocked_reason_codes))


def test_no_raw_action_payload_only_capability_id() -> None:
    """Decision models reference capability id string only (no action body)."""
    pol = _policy(AutonomyLevel.LEVEL_1_ASSISTED)
    dec = evaluate_autonomous_action(pol, "cap.a")
    fields = AutonomousActionDecision.__dataclass_fields__
    assert "payload" not in fields
    assert "action" not in fields
    assert dec.permitted is True


def test_level_3_requires_stop_policy_and_operational_state() -> None:
    pol_weak = _policy(
        AutonomyLevel.LEVEL_3_CONDITIONAL_AUTONOMY,
        stop_controls_enabled=False,
    )
    d1 = evaluate_autonomous_action(pol_weak, "cap.a")
    assert d1.permitted is False
    assert "POLICY_STOP_CONTROLS_REQUIRED_FOR_LEVEL" in d1.blocked_reason_codes

    pol_ok = _policy(
        AutonomyLevel.LEVEL_3_CONDITIONAL_AUTONOMY,
        stop_controls_enabled=True,
    )
    d2 = evaluate_autonomous_action(
        pol_ok,
        "cap.a",
        stop_control_state=StopControlState.EMERGENCY_STOP_ACTIVE,
    )
    assert d2.permitted is False
    assert "EMERGENCY_STOP_ACTIVE" in d2.blocked_reason_codes


def test_level_4_requires_kill_switch_policy_and_not_engaged() -> None:
    pol_weak = _policy(
        AutonomyLevel.LEVEL_4_HIGH_AUTONOMY,
        stop_controls_enabled=True,
        kill_switch_enabled=False,
    )
    assert evaluate_autonomous_action(pol_weak, "cap.a").permitted is False

    pol_ok = _policy(
        AutonomyLevel.LEVEL_4_HIGH_AUTONOMY,
        stop_controls_enabled=True,
        kill_switch_enabled=True,
    )
    d = evaluate_autonomous_action(
        pol_ok,
        "cap.a",
        kill_switch_state=KillSwitchState.ENGAGED,
    )
    assert d.permitted is False
    assert "KILL_SWITCH_ENGAGED" in d.blocked_reason_codes


def test_human_checkpoint_derivation_level_0() -> None:
    pol = _policy(AutonomyLevel.LEVEL_0_MANUAL)
    dec = evaluate_autonomous_action(pol, "cap.a")
    assert human_checkpoint_for_decision(pol, dec).value == "HUMAN_EXECUTION_REQUIRED"
