# Multi-tenant governance and enterprise RBAC

This section describes **enterprise multi-tenant governance** for GovAI: tenant isolation models, RBAC hierarchies, delegated administration, environment segmentation, and separation-of-duties (SoD). It complements runtime concepts in [`../security/tenant-isolation.md`](../security/tenant-isolation.md) with **operator-facing** contracts and review checklists.

## Machine-readable bundle

| File | Purpose |
| --- | --- |
| [`../../multi-tenant/governance-manifest.json`](../../multi-tenant/governance-manifest.json) | Index of artefacts, documentation paths, and explicit non-goals. |
| [`../../multi-tenant/tenant-isolation-model.json`](../../multi-tenant/tenant-isolation-model.json) | Isolation layers and cross-tenant denies. |
| [`../../multi-tenant/role-hierarchy.json`](../../multi-tenant/role-hierarchy.json) | Platform and tenant-scoped roles, inheritance, permission labels. |
| [`../../multi-tenant/delegated-administration.json`](../../multi-tenant/delegated-administration.json) | Scoped admins, break-glass, attestations. |
| [`../../multi-tenant/environment-segmentation.json`](../../multi-tenant/environment-segmentation.json) | Environment tags, secrets, promotion rules. |
| [`../../multi-tenant/separation-of-duties.json`](../../multi-tenant/separation-of-duties.json) | Mutually exclusive roles and dual-control actions. |

## Narrative guides

| Topic | Document |
| --- | --- |
| Scope and principles | [overview.md](overview.md) |
| Isolation model | [tenant-isolation-model.md](tenant-isolation-model.md) |
| RBAC hierarchy | [rbac-hierarchy.md](rbac-hierarchy.md) |
| Delegated administration | [delegated-administration.md](delegated-administration.md) |
| Environment segmentation | [environment-segmentation.md](environment-segmentation.md) |
| Separation of duties | [separation-of-duties.md](separation-of-duties.md) |

## Validation

From the repository root:

```bash
python3 scripts/multi_tenant_check.py
make multi-tenant-check
make tenant-isolation-check
```

These checks assert file presence, JSON shape, Makefile wiring, and example paths. They do **not** change compliance verdict semantics or Rust runtime enforcement.
