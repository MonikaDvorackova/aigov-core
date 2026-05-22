# Delegation risk management

Delegation introduces **sprawl**, **lateral movement**, and **confused deputy** risks when agents act on behalf of users or tenants they should not represent.

## Risk themes

- **Cross-tenant leakage**: `cross_tenant_delegation_observed` in snapshots flags edges that cross isolation boundaries.
- **Scope sprawl**: many unrelated scopes on one agent increases blast radius if compromised.
- **Deep chains**: long paths obscure who ultimately authorised an action.

## Mitigations

Combine [Delegation policies](delegation-policies.md), [Approval chains](approval-chains.md), and [Override governance](override-governance.md). Use scoring output as a **triage signal**, not an automatic block, unless your organisation wires it into CI policy.

## Scoring note

`agent_governance_score.py` uses deterministic heuristics aligned with this document’s themes. Tune thresholds in your fork if your risk appetite differs.
