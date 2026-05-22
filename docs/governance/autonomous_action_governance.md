# Autonomous action governance (Phase 4)

**Status:** **Planning and pure Python planning helpers only.** The module `python/aigov_py/autonomous_action_governance.py` provides **deterministic, side-effect-free** evaluation of **policy metadata** against a requested **`capability_id`** (no raw action payload). **No** runtime enforcement hooks, **no** database changes, **no** ledger writes, **no** API behavior changes.

This document participates in the **Phase 4 M1–M7** foundation set. For consolidated status/boundaries/integration mapping and forward roadmap, see **`phase4_multi_agent_governance.md`**.

## Purpose

Define a **formal governance model** for **autonomous agent actions**: autonomy levels, authorization requirements, human checkpoints, emergency stop and kill-switch expectations, and **accountability metadata** for audits and technical documentation.

This bridges **technical controls** (stop controls, kill switch, capability allow lists) with **governance** (approval modes, dual control, explicit overrides).

## Autonomy levels (ordinal scale)

Higher numeric levels denote **greater delegated autonomy** when acting without synchronous human initiation. **Stricter structural controls** apply as autonomy rises (stop controls, kill switch, dual approval, explicit override references).

| Enum | Meaning |
|------|---------|
| **LEVEL_0_MANUAL** | Human executes external effects; agent does not run autonomously. |
| **LEVEL_1_ASSISTED** | Agent assists; narrow automation with human-centric accountability. |
| **LEVEL_2_SUPERVISED** | Agent acts within templates / supervision patterns; escalations on exception. |
| **LEVEL_3_CONDITIONAL_AUTONOMY** | Bounded autonomy when policy and stop controls are satisfied. |
| **LEVEL_4_HIGH_AUTONOMY** | Strong autonomy subject to kill-switch governance and accountability. |
| **LEVEL_5_FULL_AUTONOMY** | Maximum autonomy in model—requires **dual approval** on policy and **explicit override** reference semantics. |

## Policy schema (`AutonomousActionPolicy`)

Tenant-scoped planning record (identifiers opaque strings):

| Field | Role |
|-------|------|
| **`policy_id`** | Stable policy record id. |
| **`tenant_id`** | Tenant scope. |
| **`autonomy_level`** | One of the levels above. |
| **`allowed_capabilities`** | Set of permitted **`capability_id`** values for autonomous execution under this policy. |
| **`required_human_roles`** | Roles that must participate in approvals or oversight (planning). |
| **`requires_approval`** | Policy expects human approval before autonomous execution where applicable. |
| **`requires_dual_approval`** | Two-person control for sensitive paths. |
| **`requires_override_reference`** | Explicit override / break-glass reference required when policy demands it. |
| **`stop_controls_enabled`** | Policy asserts tenant emergency stop path is in scope. |
| **`kill_switch_enabled`** | Policy asserts platform kill-switch governance is in scope. |

## Decision schema (`AutonomousActionDecision`)

Deterministic **planning outcome** for one capability request (still **no runtime verdict** coupling):

| Field | Role |
|-------|------|
| **`permitted`** | True only if structural rules pass (capability allowed, level constraints, control states). |
| **`blocked_reason_codes`** | Stable machine codes (sorted tuple) when not permitted. |
| **`required_approvals`** | Derived approval tokens (e.g. dual approval, role hooks). |
| **`required_override`** | Whether an explicit override reference is required for accountability. |
| **`required_stop_controls`** | Whether stop-control governance applies for this level. |
| **`accountability_requirements`** | Stable accountability tags for trace and documentation (e.g. audit trace, attribution). |

**No raw action payload** is modeled—only **`capability_id`** strings align with **`agent_context`** / capability docs.

## Control states (planning)

- **`StopControlState`:** operational vs emergency stop active (blocks **LEVEL_3+** when active).
- **`KillSwitchState`:** not engaged vs engaged (blocks **LEVEL_4+** when engaged).

## Human checkpoints (`HumanCheckpointRequirement`)

Derived labels for operator UX and documentation: e.g. human execution required (**LEVEL_0**), pre-autonomous approval, dual-approval checkpoint, post-action review.

## Evaluation rules (summary)

1. **Missing or disallowed capability** → blocked (`CAPABILITY_NOT_ALLOWED`).
2. **LEVEL_0** → autonomous execution blocked (`LEVEL_0_REQUIRES_HUMAN_ACTION`).
3. **LEVEL_3+** → policy must enable stop controls; emergency stop active blocks.
4. **LEVEL_4+** → policy must enable kill-switch posture; engaged kill switch blocks.
5. **LEVEL_5** → policy must set **dual approval** and **override reference** flags together.
6. Outputs are **deterministic** (sorted codes, no I/O).

## Emergency stop and kill switch governance (conceptual)

Design keeps **layers** so no single autonomous agent can silently disable safeguards:

1. **Tenant emergency stop** — halts governed autonomous effects for a tenant or subset of agents; audited with **`principal_id`** of initiator.
2. **Platform kill switch** — operator-level disable of outbound tools / signing (last resort); runbook and communications per enterprise policy.
3. **Graduated response** — prefer rate limits and queues before full stop unless safety demands otherwise.

## Accountability

- **Humans:** Approvers and owners remain accountable for scopes they approved.
- **Agents:** Technical accountability via **signed traces** and delegation provenance; legal accountability remains with the deploying organization.
- **Planning helpers** attach **stable accountability requirement tags** for trace design—not live audit emission.

## EU AI Act and enterprise alignment

Maps **human oversight** and **meaningful intervention** to approval chains, stop visibility, and override references; **continuous learning / self-update** remains a **sensitive capability** requiring change control (see **`agent_capability_policies.md`**).

## Out of scope (this milestone)

Runtime wiring, env vars, HTTP routes, UI flows, persistence, and compliance-summary surfaces are **explicitly deferred**.
