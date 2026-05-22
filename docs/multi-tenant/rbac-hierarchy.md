# RBAC hierarchy

The [`role-hierarchy.json`](../../multi-tenant/role-hierarchy.json) file defines **platform roles**, **tenant-scoped roles**, inheritance edges, and a flat list of **permission labels** used in governance conversations.

## Platform vs tenant scope

- **Platform roles** apply to the operator’s own staff (for example superadmin or read-only support). These must not silently inherit tenant administrative rights.
- **Tenant roles** apply within a single customer boundary. Inheritance flows from read-only auditor upward toward operators and administrators.

## Permission labels

Permission labels (such as `evidence.export` or `environment.promote_production`) are **documentation and review aids**. Product code may map them to concrete APIs or UI surfaces; this bundle does not change how verdicts are computed.

## Reviews

During access reviews, auditors should:

1. Enumerate users holding `tenant_admin` or `platform_superadmin`.
2. Verify SoD rules in [`separation-of-duties.md`](separation-of-duties.md) are reflected in the identity provider groups.
3. Confirm dormant delegations are revoked.
