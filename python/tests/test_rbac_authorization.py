from __future__ import annotations

from pathlib import Path

import yaml

from aigov_py.rbac import AuthorizationContext, PermissionBinding, evaluate_permission


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_rbac_fixtures() -> tuple[set[str], dict[str, set[str]]]:
    root = _repo_root()
    perms = _load_yaml(root / "docs/governance/rbac_permissions.v1.yaml")
    roles = _load_yaml(root / "docs/governance/rbac_roles.v1.yaml")

    known_permissions = {p["permission_id"].strip() for p in perms["permissions"]}
    role_permissions = {r["role_id"].strip(): {p.strip() for p in r["permissions"]} for r in roles["roles"]}
    return known_permissions, role_permissions


def test_tenant_admin_allowed() -> None:
    known_permissions, role_permissions = _load_rbac_fixtures()
    bindings = [PermissionBinding(tenant_id="t1", role_id="TENANT_ADMIN", scope_type="tenant")]
    ctx = AuthorizationContext(tenant_id="t1", team_id="teamA", project_id="proj1")
    assert (
        evaluate_permission(
            permission_id="policy.activate",
            ctx=ctx,
            bindings=bindings,
            role_permissions=role_permissions,
            known_permissions=known_permissions,
        )
        is True
    )


def test_operator_denied_admin_actions() -> None:
    known_permissions, role_permissions = _load_rbac_fixtures()
    bindings = [PermissionBinding(tenant_id="t1", role_id="OPERATOR", scope_type="tenant")]
    ctx = AuthorizationContext(tenant_id="t1")
    assert (
        evaluate_permission(
            permission_id="rbac.manage",
            ctx=ctx,
            bindings=bindings,
            role_permissions=role_permissions,
            known_permissions=known_permissions,
        )
        is False
    )


def test_project_scope_isolation() -> None:
    known_permissions, role_permissions = _load_rbac_fixtures()
    bindings = [PermissionBinding(tenant_id="t1", role_id="OPERATOR", scope_type="project", project_id="p1")]

    ctx_ok = AuthorizationContext(tenant_id="t1", project_id="p1")
    ctx_no = AuthorizationContext(tenant_id="t1", project_id="p2")

    assert (
        evaluate_permission(
            permission_id="runtime.evaluate",
            ctx=ctx_ok,
            bindings=bindings,
            role_permissions=role_permissions,
            known_permissions=known_permissions,
        )
        is True
    )
    assert (
        evaluate_permission(
            permission_id="runtime.evaluate",
            ctx=ctx_no,
            bindings=bindings,
            role_permissions=role_permissions,
            known_permissions=known_permissions,
        )
        is False
    )


def test_team_scope_isolation() -> None:
    known_permissions, role_permissions = _load_rbac_fixtures()
    bindings = [PermissionBinding(tenant_id="t1", role_id="APPROVER", scope_type="team", team_id="teamA")]

    ctx_ok = AuthorizationContext(tenant_id="t1", team_id="teamA", project_id="p1")
    ctx_no = AuthorizationContext(tenant_id="t1", team_id="teamB", project_id="p1")

    assert (
        evaluate_permission(
            permission_id="override.approve",
            ctx=ctx_ok,
            bindings=bindings,
            role_permissions=role_permissions,
            known_permissions=known_permissions,
        )
        is True
    )
    assert (
        evaluate_permission(
            permission_id="override.approve",
            ctx=ctx_no,
            bindings=bindings,
            role_permissions=role_permissions,
            known_permissions=known_permissions,
        )
        is False
    )


def test_unknown_permission_denied() -> None:
    known_permissions, role_permissions = _load_rbac_fixtures()
    bindings = [PermissionBinding(tenant_id="t1", role_id="TENANT_ADMIN", scope_type="tenant")]
    ctx = AuthorizationContext(tenant_id="t1")
    assert (
        evaluate_permission(
            permission_id="does.not.exist",
            ctx=ctx,
            bindings=bindings,
            role_permissions=role_permissions,
            known_permissions=known_permissions,
        )
        is False
    )


def test_unknown_role_denied() -> None:
    known_permissions, role_permissions = _load_rbac_fixtures()
    bindings = [PermissionBinding(tenant_id="t1", role_id="UNKNOWN_ROLE", scope_type="tenant")]
    ctx = AuthorizationContext(tenant_id="t1")
    assert (
        evaluate_permission(
            permission_id="runtime.read",
            ctx=ctx,
            bindings=bindings,
            role_permissions=role_permissions,
            known_permissions=known_permissions,
        )
        is False
    )


def test_cross_tenant_denied() -> None:
    known_permissions, role_permissions = _load_rbac_fixtures()
    bindings = [PermissionBinding(tenant_id="t2", role_id="TENANT_ADMIN", scope_type="tenant")]
    ctx = AuthorizationContext(tenant_id="t1")
    assert (
        evaluate_permission(
            permission_id="policy.activate",
            ctx=ctx,
            bindings=bindings,
            role_permissions=role_permissions,
            known_permissions=known_permissions,
        )
        is False
    )


def test_deterministic_repeated_evaluation() -> None:
    known_permissions, role_permissions = _load_rbac_fixtures()
    bindings = [
        PermissionBinding(tenant_id="t1", role_id="OPERATOR", scope_type="project", project_id="p1"),
        PermissionBinding(tenant_id="t1", role_id="AUDITOR_READONLY", scope_type="project", project_id="p1"),
    ]
    ctx = AuthorizationContext(tenant_id="t1", project_id="p1")
    results = [
        evaluate_permission(
            permission_id="runtime.read",
            ctx=ctx,
            bindings=bindings,
            role_permissions=role_permissions,
            known_permissions=known_permissions,
        )
        for _ in range(25)
    ]
    assert results == [True] * 25


def test_malformed_binding_fails_safely() -> None:
    known_permissions, role_permissions = _load_rbac_fixtures()
    # Missing team_id for a team scope binding is malformed; should deny without raising.
    bindings = [PermissionBinding(tenant_id="t1", role_id="APPROVER", scope_type="team", team_id=None)]
    ctx = AuthorizationContext(tenant_id="t1", team_id="teamA")
    assert (
        evaluate_permission(
            permission_id="override.approve",
            ctx=ctx,
            bindings=bindings,
            role_permissions=role_permissions,
            known_permissions=known_permissions,
        )
        is False
    )


def test_omitting_known_permissions_denies_even_if_role_contains_permission() -> None:
    _known_permissions, role_permissions = _load_rbac_fixtures()
    bindings = [PermissionBinding(tenant_id="t1", role_id="TENANT_ADMIN", scope_type="tenant")]
    ctx = AuthorizationContext(tenant_id="t1")
    assert (
        evaluate_permission(
            permission_id="policy.activate",
            ctx=ctx,
            bindings=bindings,
            role_permissions=role_permissions,
            known_permissions=None,
        )
        is False
    )


def test_empty_known_permissions_denies() -> None:
    _known_permissions, role_permissions = _load_rbac_fixtures()
    bindings = [PermissionBinding(tenant_id="t1", role_id="TENANT_ADMIN", scope_type="tenant")]
    ctx = AuthorizationContext(tenant_id="t1")
    assert (
        evaluate_permission(
            permission_id="policy.activate",
            ctx=ctx,
            bindings=bindings,
            role_permissions=role_permissions,
            known_permissions=set(),
        )
        is False
    )

