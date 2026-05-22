//! Runtime enforcement helpers for autonomous governance (ledger ingest path).
//! Logic is aligned with `python/aigov_py/autonomous_action_governance.py` (deterministic, no I/O here).

use serde_json::Value;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StopControlState {
    Operational,
    EmergencyStopActive,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KillSwitchState {
    NotEngaged,
    Engaged,
}

#[derive(Debug, Clone)]
pub struct LoadedAutonomyPolicy {
    pub autonomy_level: i16,
    pub allowed_capabilities: Vec<String>,
    pub required_human_roles: Vec<String>,
    pub requires_approval: bool,
    pub requires_dual_approval: bool,
    pub requires_override_reference: bool,
    pub stop_controls_enabled: bool,
    pub kill_switch_enabled: bool,
    pub emergency_stop_engaged: bool,
    pub kill_switch_engaged: bool,
}

#[derive(Debug, Clone)]
pub struct AutonomyEvaluationOutcome {
    pub permitted: bool,
    pub blocked_reason_codes: Vec<String>,
}

const REASON_CAPABILITY_NOT_ALLOWED: &str = "CAPABILITY_NOT_ALLOWED";
const REASON_EMPTY_CAPABILITY: &str = "EMPTY_CAPABILITY_ID";
const REASON_LEVEL_0_MANUAL: &str = "LEVEL_0_REQUIRES_HUMAN_ACTION";
const REASON_POLICY_STOP_CONTROLS: &str = "POLICY_STOP_CONTROLS_REQUIRED_FOR_LEVEL";
const REASON_POLICY_KILL_SWITCH: &str = "POLICY_KILL_SWITCH_REQUIRED_FOR_LEVEL";
const REASON_POLICY_LEVEL_5: &str = "POLICY_LEVEL_5_REQUIRES_DUAL_APPROVAL_AND_OVERRIDE";
const REASON_EMERGENCY_STOP: &str = "EMERGENCY_STOP_ACTIVE";
const REASON_KILL_SWITCH: &str = "KILL_SWITCH_ENGAGED";

fn norm_cap(s: &str) -> String {
    s.trim().to_string()
}

fn capability_allowed(policy: &LoadedAutonomyPolicy, cap: &str) -> bool {
    if policy.allowed_capabilities.iter().any(|x| x.trim() == "*") {
        return !cap.is_empty();
    }
    policy.allowed_capabilities.iter().any(|x| x.trim() == cap)
}

/// Deterministic autonomous gate (mirrors `evaluate_autonomous_action` in Python).
pub fn evaluate_autonomous_action(
    policy: &LoadedAutonomyPolicy,
    requested_capability_id: &str,
    stop_control_state: StopControlState,
    kill_switch_state: KillSwitchState,
) -> AutonomyEvaluationOutcome {
    let cap = norm_cap(requested_capability_id);
    let mut blocked: Vec<String> = Vec::new();

    if cap.is_empty() {
        blocked.push(REASON_EMPTY_CAPABILITY.to_string());
    } else if !capability_allowed(policy, &cap) {
        blocked.push(REASON_CAPABILITY_NOT_ALLOWED.to_string());
    }

    let level = policy.autonomy_level.clamp(0, 5);

    if level == 0 {
        blocked.push(REASON_LEVEL_0_MANUAL.to_string());
    }

    if level >= 3 {
        if !policy.stop_controls_enabled {
            blocked.push(REASON_POLICY_STOP_CONTROLS.to_string());
        }
        if policy.emergency_stop_engaged
            || stop_control_state == StopControlState::EmergencyStopActive
        {
            blocked.push(REASON_EMERGENCY_STOP.to_string());
        }
    }

    if level >= 4 {
        if !policy.kill_switch_enabled {
            blocked.push(REASON_POLICY_KILL_SWITCH.to_string());
        }
        if policy.kill_switch_engaged || kill_switch_state == KillSwitchState::Engaged {
            blocked.push(REASON_KILL_SWITCH.to_string());
        }
    }

    if level == 5 && !(policy.requires_dual_approval && policy.requires_override_reference) {
        blocked.push(REASON_POLICY_LEVEL_5.to_string());
    }

    blocked.sort();
    blocked.dedup();
    let permitted = blocked.is_empty();
    AutonomyEvaluationOutcome {
        permitted,
        blocked_reason_codes: blocked,
    }
}

fn parse_stop(s: Option<&str>) -> StopControlState {
    match s
        .unwrap_or("OPERATIONAL")
        .trim()
        .to_ascii_uppercase()
        .as_str()
    {
        "EMERGENCY_STOP_ACTIVE" => StopControlState::EmergencyStopActive,
        _ => StopControlState::Operational,
    }
}

fn parse_kill(s: Option<&str>) -> KillSwitchState {
    match s
        .unwrap_or("NOT_ENGAGED")
        .trim()
        .to_ascii_uppercase()
        .as_str()
    {
        "ENGAGED" => KillSwitchState::Engaged,
        _ => KillSwitchState::NotEngaged,
    }
}

/// When `payload.governance.autonomous_action` is present, returns capability + runtime posture from the caller.
pub fn extract_autonomous_capability_from_payload(
    payload: &Value,
) -> Option<(String, StopControlState, KillSwitchState)> {
    let gov = payload.get("governance")?;
    let aa = gov.get("autonomous_action")?;
    let cap = aa
        .get("capability_id")
        .and_then(Value::as_str)
        .map(|s| s.to_string())?;
    let stop = parse_stop(aa.get("stop_control_state").and_then(Value::as_str));
    let kill = parse_kill(aa.get("kill_switch_state").and_then(Value::as_str));
    Some((cap, stop, kill))
}

pub fn autonomy_enforcement_enabled_from_env() -> bool {
    match std::env::var("GOVAI_AUTONOMY_ENFORCEMENT") {
        Ok(s) => matches!(
            s.trim().to_ascii_lowercase().as_str(),
            "1" | "true" | "on" | "yes"
        ),
        Err(_) => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn permissive_high() -> LoadedAutonomyPolicy {
        LoadedAutonomyPolicy {
            autonomy_level: 5,
            allowed_capabilities: vec!["*".into()],
            required_human_roles: vec![],
            requires_approval: false,
            requires_dual_approval: true,
            requires_override_reference: true,
            stop_controls_enabled: true,
            kill_switch_enabled: true,
            emergency_stop_engaged: false,
            kill_switch_engaged: false,
        }
    }

    #[test]
    fn level_zero_blocks() {
        let p = LoadedAutonomyPolicy {
            autonomy_level: 0,
            allowed_capabilities: vec!["x".into()],
            required_human_roles: vec![],
            requires_approval: false,
            requires_dual_approval: false,
            requires_override_reference: false,
            stop_controls_enabled: false,
            kill_switch_enabled: false,
            emergency_stop_engaged: false,
            kill_switch_engaged: false,
        };
        let o = evaluate_autonomous_action(
            &p,
            "x",
            StopControlState::Operational,
            KillSwitchState::NotEngaged,
        );
        assert!(!o.permitted);
        assert!(o
            .blocked_reason_codes
            .contains(&REASON_LEVEL_0_MANUAL.to_string()));
    }

    #[test]
    fn level_five_requires_dual_and_override_on_policy() {
        let mut p = permissive_high();
        p.requires_dual_approval = false;
        let o = evaluate_autonomous_action(
            &p,
            "cap",
            StopControlState::Operational,
            KillSwitchState::NotEngaged,
        );
        assert!(!o.permitted);
        assert!(o
            .blocked_reason_codes
            .contains(&REASON_POLICY_LEVEL_5.to_string()));
    }

    #[test]
    fn emergency_stop_blocks_when_level_ge_3() {
        let p = LoadedAutonomyPolicy {
            autonomy_level: 3,
            allowed_capabilities: vec!["*".into()],
            required_human_roles: vec![],
            requires_approval: false,
            requires_dual_approval: false,
            requires_override_reference: false,
            stop_controls_enabled: true,
            kill_switch_enabled: true,
            emergency_stop_engaged: false,
            kill_switch_engaged: false,
        };
        let o = evaluate_autonomous_action(
            &p,
            "cap",
            StopControlState::EmergencyStopActive,
            KillSwitchState::NotEngaged,
        );
        assert!(!o.permitted);
        assert!(o
            .blocked_reason_codes
            .contains(&REASON_EMERGENCY_STOP.to_string()));
    }

    #[test]
    fn extract_payload_reads_nested_governance() {
        let v: Value = serde_json::json!({
            "governance": {
                "autonomous_action": {
                    "capability_id": " promote ",
                    "stop_control_state": "OPERATIONAL",
                    "kill_switch_state": "ENGAGED"
                }
            }
        });
        let (c, _, k) = extract_autonomous_capability_from_payload(&v).unwrap();
        assert_eq!(c.trim(), "promote");
        assert_eq!(k, KillSwitchState::Engaged);
    }
}
