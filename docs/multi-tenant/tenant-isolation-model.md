# Tenant isolation model

The [`tenant-isolation-model.json`](../../multi-tenant/tenant-isolation-model.json) artefact captures **isolation layers** and **explicit cross-tenant denies** used in architecture reviews.

## Layers

| Layer | Intent |
| --- | --- |
| Identity | Bind every request to a tenant through server-side credential mapping. |
| Data | Scope ledger rows, exports, and derived artefacts to the tenant key. |
| Network | Use private connectivity and egress controls where regulators expect network segmentation. |
| Observability | Emit tenant dimensions without embedding sensitive payloads in shared pipelines. |

## Cross-tenant denies

The model lists prohibited patterns such as cross-tenant evidence reads and replay of digests across tenants. Operators should map each item to concrete controls (tests, monitors, or access reviews).

## Shared services

Some components (for example static CDNs) may be shared. The policy requires **tenant namespacing** for any shared cache or configuration path so keys cannot collide across customers.

## Break-glass visibility

Administrative visibility into tenant data is expected to follow **break-glass** procedures with dual control, aligned with [`delegated-administration.md`](delegated-administration.md).
