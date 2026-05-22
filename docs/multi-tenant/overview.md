# Overview

Enterprise buyers expect **predictable isolation**, **least privilege**, and **separation of duties** layered on top of the GovAI audit service. This documentation set, together with the [`../../multi-tenant/governance-manifest.json`](../../multi-tenant/governance-manifest.json) index and sibling JSON artefacts, gives security and platform teams a **shared vocabulary** for design reviews and procurement questionnaires.

## Principles

1. **Server-owned boundaries** — Tenant identity and ledger scope are enforced by the service from credentials, not from client-selected headers alone. See [`../security/tenant-isolation.md`](../security/tenant-isolation.md).
2. **Layered isolation** — Identity, data, network, and observability each have explicit controls; gaps in one layer must not collapse the whole model.
3. **Role clarity** — Platform roles and tenant-scoped roles are defined separately so escalation paths remain auditable.
4. **Delegation with expiry** — Scoped administrators receive **time-bound** rights with recorded rationale.
5. **SoD by construction** — Mutually exclusive role sets and dual control on sensitive actions reduce insider risk.

## What is out of scope

The JSON artefacts and validators do **not**:

- modify `VALID`, `INVALID`, or `BLOCKED` semantics;
- replace database migrations or storage layout;
- implement authorization in the Rust runtime (this repository’s enforcement code is unchanged by this phase).

## Related material

- Hosted productization snapshots: [`../hosted-platform/README.md`](../hosted-platform/README.md)
- Control plane governance posture: [`../control-plane/README.md`](../control-plane/README.md)
