# Autonomous and multi-agent governance

This section documents an **operator-facing governance framework** for systems where multiple agents act with partial autonomy: role models, delegation, approval boundaries, autonomy limits, intervention points, and offline validation tooling.

The framework is **advisory**: it complements [`../agent-governance/README.md`](../agent-governance/README.md) and the enterprise [`../control-plane/README.md`](../control-plane/README.md) bundle without changing GovAI `VALID` / `INVALID` / `BLOCKED` semantics.

## Contents

- [Role models](role-models.md) — stable `role_id` identifiers and `authority_scope` labels.
- [Delegation and approval boundaries](delegation-and-approval-boundaries.md) — which delegations are allowed, forbidden edges, and when humans must approve.
- [Autonomy limits and interventions](autonomy-limits-and-interventions.md) — rate and session caps plus halt / escalate / degrade responses.
- [Multi-agent coordination](multi-agent-coordination.md) — supervisor patterns, shared state, and approval gateways between agents.
- [Validation tooling](validation-tooling.md) — `scripts/autonomous_governance_check.py` and Makefile targets.

## Machine-readable bundle

Canonical JSON lives under [`../../autonomous/autonomous-governance-manifest.json`](../../autonomous/autonomous-governance-manifest.json) (manifest + role models + boundaries + limits + intervention catalogue). Validate locally with `python3 scripts/autonomous_governance_check.py` or `make autonomous-governance-check`.
