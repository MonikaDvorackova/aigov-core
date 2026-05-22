from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Iterable

import yaml

ALLOWED_RISK_CLASSES: set[str] = {"MINIMAL", "LIMITED", "HIGH", "PROHIBITED"}
ALLOWED_MAPPING_STRENGTH: set[str] = {"REQUIRED", "RECOMMENDED", "CONTEXTUAL"}
ALLOWED_REASON_SEVERITY: set[str] = {"INFO", "WARN", "BLOCKING"}
ALLOWED_RBAC_SCOPE_TYPES: set[str] = {"tenant", "team", "project"}

_PERMISSION_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


class GovernanceCatalogError(ValueError):
    pass


def _require_dict(obj: Any, *, where: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise GovernanceCatalogError(f"{where} must be an object")
    return obj


def _require_list(obj: dict[str, Any], key: str, *, where: str) -> list[Any]:
    v = obj.get(key)
    if not isinstance(v, list):
        raise GovernanceCatalogError(f"{where}.{key} must be a list")
    return v


def _require_nonempty_str(obj: dict[str, Any], key: str, *, where: str) -> str:
    v = obj.get(key)
    if not isinstance(v, str) or not v.strip():
        raise GovernanceCatalogError(f"{where}.{key} must be a non-empty string")
    return v.strip()


def _optional_bool(obj: dict[str, Any], key: str, *, where: str) -> bool | None:
    if key not in obj:
        return None
    v = obj.get(key)
    if not isinstance(v, bool):
        raise GovernanceCatalogError(f"{where}.{key} must be a boolean if present")
    return v


def _optional_str_list(obj: dict[str, Any], key: str, *, where: str) -> list[str] | None:
    if key not in obj:
        return None
    v = obj.get(key)
    if not isinstance(v, list):
        raise GovernanceCatalogError(f"{where}.{key} must be a list of strings if present")
    out: list[str] = []
    for i, item in enumerate(v):
        if not isinstance(item, str) or not item.strip():
            raise GovernanceCatalogError(f"{where}.{key}[{i}] must be a non-empty string")
        out.append(item.strip())
    return out


def _validate_risk_class_list(values: Any, *, where: str) -> None:
    if not isinstance(values, list) or not values:
        raise GovernanceCatalogError(f"{where} must be a non-empty list")
    for i, rc in enumerate(values):
        if not isinstance(rc, str):
            raise GovernanceCatalogError(f"{where}[{i}] must be a string")
        if rc not in ALLOWED_RISK_CLASSES:
            raise GovernanceCatalogError(f"{where}[{i}] invalid risk class: {rc}")


def _validate_deprecated_and_supersedes(obj: dict[str, Any], *, where: str) -> None:
    _ = _optional_bool(obj, "deprecated", where=where)
    supersedes = _optional_str_list(obj, "supersedes", where=where)
    if supersedes is not None and not supersedes:
        raise GovernanceCatalogError(f"{where}.supersedes must not be empty if present")


def _load_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise GovernanceCatalogError(f"{path}: top-level YAML must be an object")
    return raw


@dataclass(frozen=True)
class GovernanceCatalogPaths:
    controls: Path
    requirements: Path
    mappings: Path
    reason_codes: Path
    rbac_roles: Path
    rbac_permissions: Path


def default_governance_paths(repo_root: Path) -> GovernanceCatalogPaths:
    base = repo_root / "docs" / "governance"
    return GovernanceCatalogPaths(
        controls=base / "controls.v1.yaml",
        requirements=base / "aiact_requirements.v1.yaml",
        mappings=base / "aiact_mappings.v1.yaml",
        reason_codes=base / "reason_codes.v1.yaml",
        rbac_roles=base / "rbac_roles.v1.yaml",
        rbac_permissions=base / "rbac_permissions.v1.yaml",
    )


def validate_controls(path: Path) -> dict[str, Any]:
    raw = _load_yaml(path)
    if raw.get("schema_version") != "aigov.governance_controls.v1":
        raise GovernanceCatalogError(f"{path}: unexpected schema_version")
    controls = _require_list(raw, "controls", where="controls")
    seen: set[str] = set()
    for i, c in enumerate(controls):
        cobj = _require_dict(c, where=f"controls[{i}]")
        cid = _require_nonempty_str(cobj, "control_id", where=f"controls[{i}]")
        if cid in seen:
            raise GovernanceCatalogError(f"duplicate control_id: {cid}")
        seen.add(cid)

        _ = _require_nonempty_str(cobj, "name", where=f"controls[{i}]")
        _ = _require_nonempty_str(cobj, "description", where=f"controls[{i}]")
        _validate_risk_class_list(
            cobj.get("risk_class_applicability"), where=f"controls[{i}].risk_class_applicability"
        )

        tags = cobj.get("tags")
        if not isinstance(tags, list) or not all(isinstance(t, str) and t.strip() for t in tags):
            raise GovernanceCatalogError(f"controls[{i}].tags must be a non-empty list of strings")

        ev = _require_list(cobj, "evidence_requirements", where=f"controls[{i}]")
        if not ev:
            raise GovernanceCatalogError(f"controls[{i}].evidence_requirements must be non-empty")
        for j, e in enumerate(ev):
            eobj = _require_dict(e, where=f"controls[{i}].evidence_requirements[{j}]")
            _ = _require_nonempty_str(eobj, "evidence_type", where=f"controls[{i}].evidence_requirements[{j}]")
            fields = eobj.get("required_fields")
            if not isinstance(fields, list) or not all(isinstance(x, str) and x.strip() for x in fields):
                raise GovernanceCatalogError(
                    f"controls[{i}].evidence_requirements[{j}].required_fields must be a non-empty list of strings"
                )

        policy_links = cobj.get("policy_links")
        if policy_links is not None:
            if not isinstance(policy_links, list):
                raise GovernanceCatalogError(f"controls[{i}].policy_links must be a list if present")
            for j, pl in enumerate(policy_links):
                plobj = _require_dict(pl, where=f"controls[{i}].policy_links[{j}]")
                _ = _require_nonempty_str(plobj, "policy_id", where=f"controls[{i}].policy_links[{j}]")
                _ = _require_nonempty_str(plobj, "anchor", where=f"controls[{i}].policy_links[{j}]")

        _validate_deprecated_and_supersedes(cobj, where=f"controls[{i}]")
    return raw


def validate_aiact_requirements(path: Path) -> dict[str, Any]:
    raw = _load_yaml(path)
    if raw.get("schema_version") != "aigov.aiact_requirements.v1":
        raise GovernanceCatalogError(f"{path}: unexpected schema_version")
    reqs = _require_list(raw, "requirements", where="requirements")
    seen: set[str] = set()
    for i, r in enumerate(reqs):
        robj = _require_dict(r, where=f"requirements[{i}]")
        rid = _require_nonempty_str(robj, "requirement_id", where=f"requirements[{i}]")
        if rid in seen:
            raise GovernanceCatalogError(f"duplicate requirement_id: {rid}")
        seen.add(rid)
        _ = _require_nonempty_str(robj, "article_ref", where=f"requirements[{i}]")
        _ = _require_nonempty_str(robj, "title", where=f"requirements[{i}]")
        _ = _require_nonempty_str(robj, "description", where=f"requirements[{i}]")
        _validate_risk_class_list(
            robj.get("risk_class_applicability"), where=f"requirements[{i}].risk_class_applicability"
        )
        _validate_deprecated_and_supersedes(robj, where=f"requirements[{i}]")
    return raw


def validate_aiact_mappings(
    path: Path, *, known_controls: set[str], known_requirements: set[str]
) -> dict[str, Any]:
    raw = _load_yaml(path)
    if raw.get("schema_version") != "aigov.aiact_mappings.v1":
        raise GovernanceCatalogError(f"{path}: unexpected schema_version")
    mappings = _require_list(raw, "mappings", where="mappings")
    for i, m in enumerate(mappings):
        mobj = _require_dict(m, where=f"mappings[{i}]")
        rid = _require_nonempty_str(mobj, "requirement_id", where=f"mappings[{i}]")
        cid = _require_nonempty_str(mobj, "control_id", where=f"mappings[{i}]")
        if rid not in known_requirements:
            raise GovernanceCatalogError(f"mappings[{i}].requirement_id references unknown requirement_id: {rid}")
        if cid not in known_controls:
            raise GovernanceCatalogError(f"mappings[{i}].control_id references unknown control_id: {cid}")
        ms = _require_nonempty_str(mobj, "mapping_strength", where=f"mappings[{i}]")
        if ms not in ALLOWED_MAPPING_STRENGTH:
            raise GovernanceCatalogError(f"mappings[{i}].mapping_strength invalid: {ms}")

        _validate_risk_class_list(
            mobj.get("applicability_risk_classes"), where=f"mappings[{i}].applicability_risk_classes"
        )
        _ = _require_nonempty_str(mobj, "rationale", where=f"mappings[{i}]")
        _validate_deprecated_and_supersedes(mobj, where=f"mappings[{i}]")
    return raw


def validate_reason_code_registry(path: Path, *, known_controls: set[str]) -> dict[str, Any]:
    raw = _load_yaml(path)
    if raw.get("schema_version") != "aigov.reason_code_registry.v1":
        raise GovernanceCatalogError(f"{path}: unexpected schema_version")
    items = _require_list(raw, "reason_codes", where="reason_codes")
    seen: set[str] = set()
    for i, r in enumerate(items):
        robj = _require_dict(r, where=f"reason_codes[{i}]")
        code = _require_nonempty_str(robj, "reason_code", where=f"reason_codes[{i}]")
        if code in seen:
            raise GovernanceCatalogError(f"duplicate reason_code: {code}")
        seen.add(code)
        cid = _require_nonempty_str(robj, "control_id", where=f"reason_codes[{i}]")
        if cid not in known_controls:
            raise GovernanceCatalogError(f"reason_codes[{i}].control_id references unknown control_id: {cid}")
        sev = _require_nonempty_str(robj, "severity", where=f"reason_codes[{i}]")
        if sev not in ALLOWED_REASON_SEVERITY:
            raise GovernanceCatalogError(f"reason_codes[{i}].severity invalid: {sev}")
        _ = _require_nonempty_str(robj, "description", where=f"reason_codes[{i}]")
        _validate_deprecated_and_supersedes(robj, where=f"reason_codes[{i}]")
    return raw


def validate_rbac_permissions(path: Path) -> dict[str, Any]:
    raw = _load_yaml(path)
    if raw.get("schema_version") != "aigov.rbac_permissions.v1":
        raise GovernanceCatalogError(f"{path}: unexpected schema_version")
    items = _require_list(raw, "permissions", where="permissions")
    seen: set[str] = set()
    for i, p in enumerate(items):
        pobj = _require_dict(p, where=f"permissions[{i}]")
        pid = _require_nonempty_str(pobj, "permission_id", where=f"permissions[{i}]")
        if pid in seen:
            raise GovernanceCatalogError(f"duplicate permission_id: {pid}")
        seen.add(pid)
        if _PERMISSION_ID_RE.match(pid) is None:
            raise GovernanceCatalogError(f"permissions[{i}].permission_id invalid: {pid}")
        _ = _require_nonempty_str(pobj, "description", where=f"permissions[{i}]")
        _validate_deprecated_and_supersedes(pobj, where=f"permissions[{i}]")
    return raw


def validate_rbac_roles(path: Path, *, known_permissions: set[str]) -> dict[str, Any]:
    raw = _load_yaml(path)
    if raw.get("schema_version") != "aigov.rbac_roles.v1":
        raise GovernanceCatalogError(f"{path}: unexpected schema_version")
    roles = _require_list(raw, "roles", where="roles")
    seen: set[str] = set()
    for i, r in enumerate(roles):
        robj = _require_dict(r, where=f"roles[{i}]")
        rid = _require_nonempty_str(robj, "role_id", where=f"roles[{i}]")
        if rid in seen:
            raise GovernanceCatalogError(f"duplicate role_id: {rid}")
        seen.add(rid)
        _ = _require_nonempty_str(robj, "name", where=f"roles[{i}]")
        _ = _require_nonempty_str(robj, "description", where=f"roles[{i}]")

        scopes = robj.get("allowed_scope_types")
        if not isinstance(scopes, list) or not scopes:
            raise GovernanceCatalogError(f"roles[{i}].allowed_scope_types must be a non-empty list")
        scope_set: set[str] = set()
        for j, s in enumerate(scopes):
            if not isinstance(s, str) or not s.strip():
                raise GovernanceCatalogError(f"roles[{i}].allowed_scope_types[{j}] must be a non-empty string")
            st = s.strip()
            if st not in ALLOWED_RBAC_SCOPE_TYPES:
                raise GovernanceCatalogError(f"roles[{i}].allowed_scope_types[{j}] invalid scope type: {st}")
            scope_set.add(st)
        if len(scope_set) != len(scopes):
            raise GovernanceCatalogError(f"roles[{i}].allowed_scope_types must not contain duplicates")

        perms = robj.get("permissions")
        if not isinstance(perms, list) or not perms:
            raise GovernanceCatalogError(f"roles[{i}].permissions must be a non-empty list")
        for j, p in enumerate(perms):
            if not isinstance(p, str) or not p.strip():
                raise GovernanceCatalogError(f"roles[{i}].permissions[{j}] must be a non-empty string")
            pid = p.strip()
            if pid not in known_permissions:
                raise GovernanceCatalogError(f"roles[{i}].permissions[{j}] references unknown permission_id: {pid}")

        _validate_deprecated_and_supersedes(robj, where=f"roles[{i}]")
    return raw


def validate_governance_catalog(repo_root: Path) -> None:
    """
    Read-only validator for Phase 3 governance metadata.

    - Does not change runtime behavior
    - Does not write to ledger
    - Does not add/require API endpoints
    """
    paths = default_governance_paths(repo_root)

    controls_raw = validate_controls(paths.controls)
    control_ids = {c["control_id"].strip() for c in controls_raw["controls"]}

    req_raw = validate_aiact_requirements(paths.requirements)
    req_ids = {r["requirement_id"].strip() for r in req_raw["requirements"]}

    _ = validate_aiact_mappings(paths.mappings, known_controls=control_ids, known_requirements=req_ids)
    _ = validate_reason_code_registry(paths.reason_codes, known_controls=control_ids)

    perms_raw = validate_rbac_permissions(paths.rbac_permissions)
    perm_ids = {p["permission_id"].strip() for p in perms_raw["permissions"]}
    _ = validate_rbac_roles(paths.rbac_roles, known_permissions=perm_ids)


def _ids(raw: dict[str, Any], key: str, *, id_field: str) -> set[str]:
    arr = raw.get(key)
    if not isinstance(arr, list):
        return set()
    out: set[str] = set()
    for obj in arr:
        if isinstance(obj, dict) and isinstance(obj.get(id_field), str):
            out.add(obj[id_field].strip())
    return out


def validate_in_memory(
    *,
    controls: dict[str, Any],
    requirements: dict[str, Any],
    mappings: dict[str, Any],
    reason_codes: dict[str, Any],
) -> None:
    """
    Helper for tests: validate already-loaded YAML objects without IO.
    """
    controls = _require_dict(controls, where="controls")
    requirements = _require_dict(requirements, where="requirements")
    mappings = _require_dict(mappings, where="mappings")
    reason_codes = _require_dict(reason_codes, where="reason_codes")

    # Persist through the same validators by writing to temp files is unnecessary; instead we re-run
    # a minimal subset of structural checks and cross-reference resolution.
    if controls.get("schema_version") != "aigov.governance_controls.v1":
        raise GovernanceCatalogError("controls.schema_version unexpected")
    if requirements.get("schema_version") != "aigov.aiact_requirements.v1":
        raise GovernanceCatalogError("requirements.schema_version unexpected")
    if mappings.get("schema_version") != "aigov.aiact_mappings.v1":
        raise GovernanceCatalogError("mappings.schema_version unexpected")
    if reason_codes.get("schema_version") != "aigov.reason_code_registry.v1":
        raise GovernanceCatalogError("reason_codes.schema_version unexpected")

    control_ids = _ids(controls, "controls", id_field="control_id")
    req_ids = _ids(requirements, "requirements", id_field="requirement_id")

    # Reuse the full validators by serializing to YAML strings in-memory.
    # Keep it simple: enforce uniqueness + reference resolution + risk class constraints.
    # (Full file-based validators are exercised in integration tests.)
    if len(control_ids) != len(controls.get("controls", [])):
        raise GovernanceCatalogError("duplicate control_id detected")
    if len(req_ids) != len(requirements.get("requirements", [])):
        raise GovernanceCatalogError("duplicate requirement_id detected")

    for i, m in enumerate(mappings.get("mappings", []) or []):
        if not isinstance(m, dict):
            raise GovernanceCatalogError(f"mappings[{i}] must be an object")
        rid = m.get("requirement_id")
        cid = m.get("control_id")
        if rid not in req_ids:
            raise GovernanceCatalogError("mapping references unknown requirement_id")
        if cid not in control_ids:
            raise GovernanceCatalogError("mapping references unknown control_id")
        _validate_risk_class_list(m.get("applicability_risk_classes"), where=f"mappings[{i}].applicability_risk_classes")

    seen_rc: set[str] = set()
    for i, r in enumerate(reason_codes.get("reason_codes", []) or []):
        if not isinstance(r, dict):
            raise GovernanceCatalogError(f"reason_codes[{i}] must be an object")
        code = r.get("reason_code")
        if not isinstance(code, str) or not code.strip():
            raise GovernanceCatalogError("reason_code must be a non-empty string")
        if code in seen_rc:
            raise GovernanceCatalogError("duplicate reason_code detected")
        seen_rc.add(code)
        if r.get("control_id") not in control_ids:
            raise GovernanceCatalogError("reason_code references unknown control_id")

