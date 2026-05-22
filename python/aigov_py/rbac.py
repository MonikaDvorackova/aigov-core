from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

ALLOWED_SCOPE_TYPES: set[str] = {"tenant", "team", "project"}


@dataclass(frozen=True)
class PermissionBinding:
    """
    A tenant-safe binding of a role to an explicit scope.

    This file intentionally does not model subjects/users yet. It only provides
    deterministic authorization primitives used by future layers.
    """

    tenant_id: str
    role_id: str
    scope_type: str  # one of: tenant|team|project
    team_id: str | None = None
    project_id: str | None = None


@dataclass(frozen=True)
class AuthorizationContext:
    tenant_id: str
    team_id: str | None = None
    project_id: str | None = None


def _is_nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _binding_is_well_formed(binding: PermissionBinding) -> bool:
    if not _is_nonempty_str(binding.tenant_id):
        return False
    if not _is_nonempty_str(binding.role_id):
        return False
    if binding.scope_type not in ALLOWED_SCOPE_TYPES:
        return False

    if binding.scope_type == "tenant":
        return binding.team_id is None and binding.project_id is None
    if binding.scope_type == "team":
        return _is_nonempty_str(binding.team_id) and binding.project_id is None
    if binding.scope_type == "project":
        return _is_nonempty_str(binding.project_id) and binding.team_id is None
    return False


def _binding_applies(binding: PermissionBinding, ctx: AuthorizationContext) -> bool:
    # Tenant isolation is strict.
    if binding.tenant_id != ctx.tenant_id:
        return False

    if binding.scope_type == "tenant":
        return True
    if binding.scope_type == "team":
        return ctx.team_id is not None and binding.team_id == ctx.team_id
    if binding.scope_type == "project":
        return ctx.project_id is not None and binding.project_id == ctx.project_id
    return False


def evaluate_permission(
    *,
    permission_id: str,
    ctx: AuthorizationContext,
    bindings: Iterable[Any],
    role_permissions: Mapping[str, set[str]],
    known_permissions: set[str] | None,
) -> bool:
    """
    Deterministic, default-deny permission evaluation.

    Rules:
    - deny by default
    - unknown role => deny
    - unknown permission => deny
    - no wildcard escalation
    - explicit scope matching only
    - malformed bindings fail safely (treated as non-applicable)
    """

    if not _is_nonempty_str(permission_id):
        return False
    pid = permission_id.strip()
    if not known_permissions:
        return False
    if pid not in known_permissions:
        return False

    for b in bindings:
        if not isinstance(b, PermissionBinding):
            continue
        if not _binding_is_well_formed(b):
            continue
        perms = role_permissions.get(b.role_id)
        if perms is None:
            continue
        if pid not in perms:
            continue
        if _binding_applies(b, ctx):
            return True

    return False

