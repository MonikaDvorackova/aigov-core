# Delegation policies

Delegation policies constrain **which principals** may hand work to **which agents**, with **which capabilities**, and for **how long**. Good policies reduce privilege escalation and unbounded fan-out in multi-agent graphs.

## Policy elements

- **Delegator identity**: stable identifier for the orchestrator or human-initiated principal.
- **Delegate allow-list**: explicit agent identities that may receive work; avoid open-ended “any worker” patterns in regulated contexts.
- **Scope bundles**: named capability sets (for example read-only telemetry vs draft recommendations) rather than raw API keys attached to agents.
- **Depth limits**: maximum delegation hops from the root principal; deep chains complicate accountability.

## Mapping to snapshots

The delegation section of a snapshot records observed `delegator_agent_id`, `delegate_agent_ids`, `delegation_scopes`, `max_delegation_depth_observed`, and `cross_tenant_delegation_observed`. Operators compare these fields against internal policy registers during reviews.

## Related documentation

- [Approval chains](approval-chains.md) for gating high-impact scopes.
- [Delegation risk management](delegation-risk-management.md) for threat-oriented discussion.
