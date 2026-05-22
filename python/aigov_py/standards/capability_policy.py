from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from aigov_py.standards.common import (
    ValidationIssue,
    ValidationResult,
    canonical_digest,
    find_raw_content_fields,
)


class CapabilityRiskClass(str, Enum):
    MINIMAL = "MINIMAL"
    LIMITED = "LIMITED"
    HIGH = "HIGH"
    PROHIBITED = "PROHIBITED"


@dataclass(frozen=True)
class CapabilityConstraint:
    constraint_type: str
    constraint_ref: str | None = None


@dataclass(frozen=True)
class CapabilityDefinition:
    capability_id: str
    name: str
    description: str
    risk_class: CapabilityRiskClass
    allowed_tools: tuple[str, ...]
    constraints: tuple[CapabilityConstraint, ...]
    evidence_requirements: tuple[str, ...]
    ai_act_refs: tuple[str, ...]


@dataclass(frozen=True)
class CapabilityPolicyDocument:
    schema_version: str
    policy_id: str
    tenant_scope: str
    capabilities: tuple[CapabilityDefinition, ...]


def _parse_constraint(raw: Any, path: str, issues: list[ValidationIssue]) -> CapabilityConstraint | None:
    if not isinstance(raw, Mapping):
        issues.append(
            ValidationIssue(
                code="constraint_invalid",
                message="constraint must be an object",
                path=path,
            )
        )
        return None
    ct = raw.get("constraint_type")
    if not isinstance(ct, str) or not ct.strip():
        issues.append(
            ValidationIssue(
                code="constraint_type_required",
                message="constraint_type is required and must be a non-empty string",
                path=f"{path}.constraint_type",
            )
        )
        return None
    cref = raw.get("constraint_ref")
    if cref is not None and (not isinstance(cref, str) or not cref.strip()):
        issues.append(
            ValidationIssue(
                code="constraint_ref_invalid",
                message="constraint_ref must be a non-empty string when present",
                path=f"{path}.constraint_ref",
            )
        )
        return None
    return CapabilityConstraint(
        constraint_type=ct.strip(),
        constraint_ref=None if cref is None else str(cref).strip(),
    )


def _parse_capability(raw: Any, idx: int, issues: list[ValidationIssue]) -> CapabilityDefinition | None:
    base = f"capabilities[{idx}]"
    if not isinstance(raw, Mapping):
        issues.append(
            ValidationIssue(
                code="capability_invalid",
                message="each capability must be an object",
                path=base,
            )
        )
        return None
    cap_id = raw.get("capability_id")
    if not isinstance(cap_id, str) or not cap_id.strip():
        issues.append(
            ValidationIssue(
                code="capability_id_required",
                message="capability_id is required",
                path=f"{base}.capability_id",
            )
        )
        return None
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        issues.append(
            ValidationIssue(
                code="name_required",
                message="name is required",
                path=f"{base}.name",
            )
        )
    desc = raw.get("description")
    if not isinstance(desc, str):
        issues.append(
            ValidationIssue(
                code="description_invalid",
                message="description must be a string",
                path=f"{base}.description",
            )
        )
    rc_raw = raw.get("risk_class")
    risk: CapabilityRiskClass | None = None
    if isinstance(rc_raw, str):
        try:
            risk = CapabilityRiskClass(rc_raw.strip())
        except ValueError:
            issues.append(
                ValidationIssue(
                    code="risk_class_invalid",
                    message="risk_class must be one of MINIMAL, LIMITED, HIGH, PROHIBITED",
                    path=f"{base}.risk_class",
                )
            )
    else:
        issues.append(
            ValidationIssue(
                code="risk_class_invalid",
                message="risk_class must be a string",
                path=f"{base}.risk_class",
            )
        )

    tools_raw = raw.get("allowed_tools")
    tools: list[str] = []
    if not isinstance(tools_raw, list):
        issues.append(
            ValidationIssue(
                code="allowed_tools_invalid",
                message="allowed_tools must be a non-empty array of strings",
                path=f"{base}.allowed_tools",
            )
        )
    else:
        seen_t: set[str] = set()
        for j, t in enumerate(tools_raw):
            if not isinstance(t, str) or not t.strip():
                issues.append(
                    ValidationIssue(
                        code="tool_id_empty",
                        message="allowed_tools entries must be non-empty strings",
                        path=f"{base}.allowed_tools[{j}]",
                    )
                )
                continue
            tid = t.strip()
            if tid in seen_t:
                issues.append(
                    ValidationIssue(
                        code="tool_duplicate",
                        message=f"duplicate tool id in allowed_tools: {tid}",
                        path=f"{base}.allowed_tools",
                    )
                )
                continue
            seen_t.add(tid)
            tools.append(tid)
        if len(tools) == 0 and isinstance(tools_raw, list) and len(tools_raw) == 0:
            issues.append(
                ValidationIssue(
                    code="allowed_tools_empty",
                    message="allowed_tools must be non-empty",
                    path=f"{base}.allowed_tools",
                )
            )

    cons_raw = raw.get("constraints", [])
    constraints: list[CapabilityConstraint] = []
    if cons_raw is None:
        cons_raw = []
    if not isinstance(cons_raw, list):
        issues.append(
            ValidationIssue(
                code="constraints_invalid",
                message="constraints must be an array",
                path=f"{base}.constraints",
            )
        )
    else:
        for j, c in enumerate(cons_raw):
            parsed = _parse_constraint(c, f"{base}.constraints[{j}]", issues)
            if parsed is not None:
                constraints.append(parsed)

    ev_raw = raw.get("evidence_requirements")
    ev_list: list[str] = []
    if not isinstance(ev_raw, list) or len(ev_raw) == 0:
        issues.append(
            ValidationIssue(
                code="evidence_requirements_invalid",
                message="evidence_requirements must be a non-empty array of non-empty strings",
                path=f"{base}.evidence_requirements",
            )
        )
    else:
        for j, e in enumerate(ev_raw):
            if not isinstance(e, str) or not e.strip():
                issues.append(
                    ValidationIssue(
                        code="evidence_requirement_empty",
                        message="each evidence_requirement must be a non-empty string",
                        path=f"{base}.evidence_requirements[{j}]",
                    )
                )
            else:
                ev_list.append(e.strip())

    ai_raw = raw.get("ai_act_refs", [])
    ai_refs: list[str] = []
    if ai_raw is None:
        ai_raw = []
    if not isinstance(ai_raw, list):
        issues.append(
            ValidationIssue(
                code="ai_act_refs_invalid",
                message="ai_act_refs must be an array of strings when present",
                path=f"{base}.ai_act_refs",
            )
        )
    else:
        for j, a in enumerate(ai_raw):
            if not isinstance(a, str) or not a.strip():
                issues.append(
                    ValidationIssue(
                        code="ai_act_ref_empty",
                        message="each ai_act_refs entry must be a non-empty string",
                        path=f"{base}.ai_act_refs[{j}]",
                    )
                )
            else:
                ai_refs.append(a.strip())

    if risk is None:
        return None
    if not isinstance(name, str) or not name.strip():
        return None
    if not isinstance(desc, str):
        return None

    return CapabilityDefinition(
        capability_id=cap_id.strip(),
        name=name.strip(),
        description=desc,
        risk_class=risk,
        allowed_tools=tuple(tools),
        constraints=tuple(constraints),
        evidence_requirements=tuple(ev_list),
        ai_act_refs=tuple(ai_refs),
    )


def capability_policy_document_from_dict(
    data: Any,
) -> tuple[CapabilityPolicyDocument | None, tuple[ValidationIssue, ...]]:
    issues: list[ValidationIssue] = []
    if not isinstance(data, Mapping):
        return None, [ValidationIssue(code="root_invalid", message="document root must be an object", path="")]

    issues.extend(find_raw_content_fields(data))

    sv = data.get("schema_version")
    if not isinstance(sv, str) or not sv.strip():
        issues.append(
            ValidationIssue(
                code="schema_version_required",
                message="schema_version is required",
                path="schema_version",
            )
        )

    pid = data.get("policy_id")
    if not isinstance(pid, str) or not pid.strip():
        issues.append(
            ValidationIssue(
                code="policy_id_required",
                message="policy_id is required",
                path="policy_id",
            )
        )

    ts = data.get("tenant_scope")
    if not isinstance(ts, str) or not ts.strip():
        issues.append(
            ValidationIssue(
                code="tenant_scope_required",
                message="tenant_scope is required",
                path="tenant_scope",
            )
        )

    caps_raw = data.get("capabilities")
    if not isinstance(caps_raw, list) or len(caps_raw) == 0:
        issues.append(
            ValidationIssue(
                code="capabilities_required",
                message="capabilities must be a non-empty array",
                path="capabilities",
            )
        )
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))

    seen_ids: set[str] = set()
    caps: list[CapabilityDefinition] = []
    for i, raw in enumerate(caps_raw):
        c = _parse_capability(raw, i, issues)
        if c is not None:
            if c.capability_id in seen_ids:
                issues.append(
                    ValidationIssue(
                        code="capability_id_duplicate",
                        message=f"duplicate capability_id: {c.capability_id}",
                        path=f"capabilities[{i}].capability_id",
                    )
                )
                continue
            seen_ids.add(c.capability_id)
            caps.append(c)

    if not isinstance(sv, str) or not sv.strip():
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))
    if not isinstance(pid, str) or not pid.strip():
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))
    if not isinstance(ts, str) or not ts.strip():
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))

    if len(caps) == 0:
        issues.append(
            ValidationIssue(
                code="capabilities_invalid",
                message="no valid capability definitions parsed",
                path="capabilities",
            )
        )

    doc = CapabilityPolicyDocument(
        schema_version=sv.strip(),
        policy_id=pid.strip(),
        tenant_scope=ts.strip(),
        capabilities=tuple(caps),
    )
    return doc, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))


def _canonical_capability_payload(doc: CapabilityPolicyDocument) -> dict[str, Any]:
    caps_sorted = sorted(doc.capabilities, key=lambda x: x.capability_id)
    out_caps: list[dict[str, Any]] = []
    for c in caps_sorted:
        cons_sorted = sorted(
            c.constraints,
            key=lambda x: (x.constraint_type, x.constraint_ref or ""),
        )
        out_caps.append(
            {
                "ai_act_refs": list(c.ai_act_refs),
                "allowed_tools": list(c.allowed_tools),
                "capability_id": c.capability_id,
                "constraints": [
                    {
                        "constraint_ref": cc.constraint_ref,
                        "constraint_type": cc.constraint_type,
                    }
                    for cc in cons_sorted
                ],
                "description": c.description,
                "evidence_requirements": list(c.evidence_requirements),
                "name": c.name,
                "risk_class": c.risk_class.value,
            }
        )
    return {
        "capabilities": out_caps,
        "policy_id": doc.policy_id,
        "schema_version": doc.schema_version,
        "tenant_scope": doc.tenant_scope,
    }


def canonical_capability_policy_document(doc: CapabilityPolicyDocument) -> dict[str, Any]:
    return _canonical_capability_payload(doc)


def digest_capability_policy_document(doc: CapabilityPolicyDocument) -> str:
    return canonical_digest(_canonical_capability_payload(doc))


def validate_capability_policy_document(data: Any) -> ValidationResult:
    doc, parse_issues = capability_policy_document_from_dict(data)
    issues = list(parse_issues)
    if doc is None:
        return ValidationResult(ok=False, issues=tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message))))

    for i, c in enumerate(doc.capabilities):
        base = f"capabilities[{i}]"
        if len(c.allowed_tools) == 0:
            issues.append(
                ValidationIssue(
                    code="allowed_tools_empty",
                    message="allowed_tools must be non-empty",
                    path=f"{base}.allowed_tools",
                )
            )
        if len(c.evidence_requirements) == 0:
            issues.append(
                ValidationIssue(
                    code="evidence_requirements_empty",
                    message="evidence_requirements must be non-empty",
                    path=f"{base}.evidence_requirements",
                )
            )

    issues_sorted = tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))
    ok = len(issues_sorted) == 0 and doc is not None
    d = digest_capability_policy_document(doc) if ok else None
    return ValidationResult(ok=ok, issues=issues_sorted, digest=d)
