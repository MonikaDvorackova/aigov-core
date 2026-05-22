# RBAC foundation (metadata-only)

Phase 3 M2 introduces a **tenant-safe RBAC foundation** as governance metadata plus pure-Python authorization primitives.

This slice is intentionally limited:

- No runtime policy engine or enforcement changes
- No UI
- No SAML/SCIM/IdP integration
- No override workflow implementation yet
- No dataset governance workflow implementation yet
- No audit export implementation yet
- No new HTTP endpoints or API surface

## Default deny

Authorization evaluation is **deterministic** and **denies by default**:

- Unknown permission → deny
- Unknown role → deny
- Malformed binding → deny (fails safely)

There is **no wildcard escalation**.

## Scope hierarchy

Bindings are always scoped and **must match explicitly**.

Supported scope types:

- `tenant`
- `team`
- `project`

Matching rules:

- A `tenant` binding can authorize actions on **tenant/team/project** resources **within the same tenant**
- A `team` binding can authorize actions on **team/project** resources **within the same team** (and same tenant)
- A `project` binding can authorize actions on **only the exact project** (and same tenant)

Cross-tenant access is always denied.

## Metadata fixtures

RBAC metadata is defined under `docs/governance/`:

- `rbac_permissions.v1.yaml`
- `rbac_roles.v1.yaml` (roles reference permission IDs)

These files are validated by the governance catalog validator in `python/aigov_py/governance_catalog.py`.

## M7.6 future management API enforcement plan

M7.6 does **not** change runtime authorization behavior. It documents how RBAC should apply later to future management APIs only, using the default-deny and tenant-scope invariants above.

Planned management actions:

- `policy.activate`
- `policy.rollback`
- `override.approve`
- `override.revoke`
- `dataset.approve`
- `audit.export`
- `rbac.manage`

See `docs/governance/rbac_enforcement_plan.md` for required permissions, scope resolution, actor identity requirements, separation-of-duties checks, failure semantics, audit event requirements, test matrix, and NO-GO conditions.

Explicit non-goal: M7.6 does not add RBAC enforcement to `/v1/runtime/evaluate`.

