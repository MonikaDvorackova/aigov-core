# Agent capability policies (Phase 4 foundation)

**Status:** planning and architecture plus **M3 (shipped):** **shadow-only** capability consistency checks on **`POST /v1/runtime/evaluate`** — advisory rows under **`governance_summary.advisory_control_evaluations`** (**`source: capability_shadow`**), **no** hard enforcement, **no** verdict coupling. Full policy engine / RBAC / SoD enforcement remains future work.

This document participates in the **Phase 4 M1–M7** foundation set. For consolidated status/boundaries/integration mapping and forward roadmap, see **`phase4_multi_agent_governance.md`**.

## Purpose

Attach **machine-checkable limits** to **`capability_id`** for agents (and humans where relevant), including **separation of duties** between agents, **compensating controls** for high-impact **`capability_id`** sets, and **approval chain** requirements.

## Runtime shadow checks (M3)

For each evaluate call (with validated **`action`**), the service may emit advisory controls:

| Control ID | When | Severity |
|------------|------|----------|
| **`GOVAI.AGENT.CAPABILITY_DECLARED`** | **`agent_context.capability_id`** present | PASS |
| **`GOVAI.AGENT.CAPABILITY_DELEGATION_MISMATCH`** | **`delegation_context.delegated_capability_id`** present and not equal to **`agent_context.capability_id`** | WARN |
| **`GOVAI.AGENT.CAPABILITY_UNDECLARED`** | **`delegation_context`** present but neither delegated nor agent **`capability_id`** | WARN |

These rows **never** alter top-level **`verdict`**, HTTP **`enforcement`**, or merged **`governance_summary.control_evaluations`** semantics; they are **telemetry-only** for operators and trace reviewers.

## Capability registry

- Each **`capability_id`** is **versioned** (e.g. suffix or semver in metadata) so policy upgrades do not break **replay** of old traces.
- Categories (non-exhaustive): **read**, **write**, **delegate**, **approve**, **execute_external**, **configure_governance**, **emit_audit**.

## Policy attachment

Policies reference:

| Field | Role |
|-------|------|
| **`principal_id` / `agent_id`** | Who is being constrained (subject). |
| **`capability_id`** | What class of action is governed. |
| **Conditions** | Risk class, tenant, dataset tags, time windows, rate limits. |
| **Effect** | Allow, deny, allow-with-approval, shadow (observe-only). |

## Separation of duties (SoD) between agents

- **SoD rules** are tuples such as: *if **`agent_id` A** holds **`capability_id` X**, then **`agent_id` B** may not hold **`capability_id` Y** in the same **workflow scope*** (e.g. same case ID, change ticket, or transaction).
- **Typical pattern:** one agent **proposes** (draft PR, recommended action); another **validates** or **human** **approves** execution.
- **Conflicting capabilities** are declared in a **registry** (future YAML or DB) separate from RBAC roles so that **dynamic** agent fleets can be checked without hard-coding each pair.

## Approval chains across agents and humans

- A **required approval chain** is an ordered list of **steps**, each step being one of:
  - **Human role** or **`principal_id` pattern**
  - **`agent_id`** with **`capability_id: …approve…`** (approval-specialized agent)
- **Quorum** and **fallback** (e.g. on-call rotation) are policy-defined; foundation assumes **deterministic** evaluation given **policy snapshot + trace prefix**.

## Cross-agent approval and overrides

- **Cross-agent approval:** Downstream action is **committed** only after steps complete; each step emits a **signed decision event** (see `multi_agent_traceability.md`).
- **Override:** Emergency path **bypasses** normal approval **only** where **`capability_id`** allows **`override`** and **`governance.overrides`** primitives apply; **two-person rules** may be required for **HIGH** risk classes.

## Cryptographic enforcement (design intent)

- Policies may require **signing** for certain **`capability_id`** effects so that **post-hoc** verification can confirm **which key** approved (see `agent_identity.md`).

## EU AI Act and enterprise mapping (high level)

- **Art. 9 / risk management:** SoD and conditional approval reduce **undetected erroneous or malicious automation**.
- **Art. 12:** Capability-bound logging differentiates **which automated function** acted.
- **Enterprise GRC:** Maps to **compatibly** with **SoD matrices** and **change advisory** boards; **`capability_id`** aligns to **entitlement catalogs**.

## Out of scope

Concrete YAML schema extensions to `controls.v1.yaml` / RBAC files and runtime evaluation hooks are deferred to implementation milestones after foundation sign-off.
