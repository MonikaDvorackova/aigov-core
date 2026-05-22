# M7.6 RBAC enforcement plan for future management APIs

Phase 3 M7.6 is a **planning-only** design for applying existing RBAC primitives to future management APIs. It does not add endpoints, does not enforce RBAC on runtime evaluate, and does not change runtime verdict behavior.

## Scope

In scope for future enforcement:

| Management action | Required permission | Minimum scope |
|-------------------|---------------------|---------------|
| `policy.activate` | `policy.activate` | Tenant or narrower resource scope resolved to tenant |
| `policy.rollback` | `policy.rollback` | Tenant or narrower resource scope resolved to tenant |
| `override.approve` | `override.approve` | Scope of the target runtime decision |
| `override.revoke` | `override.revoke` | Scope of the approved override |
| `dataset.approve` | `dataset.approve` | Scope of the dataset registration |
| `audit.export` | `audit.export` | Scope of the requested export |
| `rbac.manage` | `rbac.manage` | Tenant scope only |

Out of scope:

- `/v1/runtime/evaluate` permission checks.
- Runtime enforcement changes.
- Compliance-summary changes.
- Database migrations.
- Ledger writes in this PR.
- New management API implementation.

## Scope resolution

Every management request must resolve a single tenant before authorization. Team and project scopes are valid only when they are anchored to the same tenant as the actor binding and target resource.

Resolution order:

1. Resolve `tenant_id` from the authenticated actor context.
2. Resolve target resource tenant from the route/body identifier.
3. Resolve optional team/project scope from the target resource metadata.
4. Deny when any tenant or scope component is missing, ambiguous, or cross-tenant.
5. Evaluate RBAC binding against the exact action permission and resolved scope.

Tenant isolation is invariant: no role binding, wildcard, or inherited scope can authorize access to a resource in another tenant. Denials must not reveal whether another tenant's resource exists.

## Actor identity requirements

Future management APIs must require an actor with:

- Stable `actor_id`.
- Resolved `tenant_id`.
- Authenticated identity source.
- Non-empty role bindings.
- Request correlation id for auditability.

Machine actors are allowed only when explicitly bound to the required permission and scope. Anonymous or partially resolved actors are denied by default.

## Default deny behavior

Authorization defaults to deny for:

- Missing actor.
- Unknown permission.
- Unknown role.
- Missing or malformed scope.
- Cross-tenant target.
- Separation-of-duties violation.
- Invalid request shape.

There is no wildcard escalation. A management action must map to exactly one required permission before enforcement is enabled.

## Separation of duties

SoD requirements apply to approval-like actions:

- `override.approve`: approving actor must differ from the actor that requested or created the override.
- `dataset.approve`: approving actor must differ from the actor that submitted the dataset registration.
- `policy.activate`: activating actor must differ from the actor that authored the candidate policy when the policy changes enforcement behavior.
- `policy.rollback`: rollback actor must be authorized independently; rollback must not reuse the original activation approval.
- `rbac.manage`: actor may not grant themselves broader scope or a new permission in the same request.

SoD violations are authorization failures and must be audited.

## Audit event requirements

Future enforcement must emit a management audit event for both allow and deny decisions. Events must include:

- `tenant_id`
- `actor_id`
- `action`
- `required_permission`
- `resolved_scope`
- `target_resource_ref`
- `decision` (`ALLOW` or `DENY`)
- `reason_code`
- `correlation_id`

Events must not include raw prompts, raw dataset records, user payloads, or other raw content. Event emission is a requirement for the future enforcement PR, not implemented by this planning bundle.

## Failure semantics

| Failure | Future response |
|---------|-----------------|
| Missing actor | `401` or `403` with stable `missing_actor` reason, depending on auth layer ownership |
| Missing permission | `403` with `missing_permission` |
| Wrong tenant/scope | `404` or `403` with `wrong_scope`, without cross-tenant existence leakage |
| SoD violation | `403` with `sod_violation` |
| Invalid request shape | `400` with `invalid_request_shape` before authorization side effects |

Failures must not fall back to allow, must not alter runtime evaluate, and must not write ledger entries unless the future enforcement PR explicitly introduces scoped audit persistence.

## Test matrix

| Area | Required tests before enforcement |
|------|-----------------------------------|
| Permission matrix | Allow/deny for each management action and permission |
| Scope resolution | Tenant, team, and project scope matches |
| Tenant isolation | Cross-tenant action denied without resource leakage |
| Actor identity | Missing actor and malformed actor denied |
| Default deny | Unknown role, unknown permission, and malformed binding denied |
| SoD | Creator/requester cannot approve their own action |
| Audit events | Allow and deny events carry required metadata only |
| Runtime evaluate | Existing runtime evaluate tests unchanged; no RBAC checks added |

## NO-GO conditions

Do not enable M7.6 enforcement until:

- Every management action has a stable permission id and owner.
- Scope resolution is deterministic and tenant-safe.
- Actor identity is available on every future management route.
- SoD metadata exists for approval-like actions.
- Audit event shape is reviewed and raw-content-free.
- Denial responses are stable and do not leak cross-tenant resource existence.
- `/v1/runtime/evaluate` remains outside the RBAC enforcement surface.
