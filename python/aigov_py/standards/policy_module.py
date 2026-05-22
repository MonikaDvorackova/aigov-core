from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from aigov_py.standards.common import (
    ValidationIssue,
    ValidationResult,
    canonical_digest,
    find_raw_content_fields,
)


@dataclass(frozen=True)
class PolicyModuleIdentity:
    id: str
    name: str
    version: str


@dataclass(frozen=True)
class PolicyModuleRequirement:
    code: str
    required_evidence: tuple[str, ...]


@dataclass(frozen=True)
class GovernancePolicyModuleDocument:
    schema_version: str
    policy: PolicyModuleIdentity
    requirements: tuple[PolicyModuleRequirement, ...]


def governance_policy_module_from_dict(
    data: Any,
) -> tuple[GovernancePolicyModuleDocument | None, tuple[ValidationIssue, ...]]:
    issues: list[ValidationIssue] = []
    if not isinstance(data, Mapping):
        return None, (ValidationIssue(code="root_invalid", message="document root must be an object", path=""),)

    issues.extend(find_raw_content_fields(data))

    sv = data.get("schema_version")
    if not isinstance(sv, str) or not sv.strip():
        issues.append(
            ValidationIssue(code="schema_version_required", message="schema_version is required", path="schema_version")
        )

    pr = data.get("policy")
    if not isinstance(pr, Mapping):
        issues.append(ValidationIssue(code="policy_required", message="policy must be an object", path="policy"))
        policy_obj: PolicyModuleIdentity | None = None
    else:
        pid = pr.get("id")
        pname = pr.get("name")
        pver = pr.get("version")
        if not isinstance(pid, str) or not pid.strip():
            issues.append(
                ValidationIssue(code="policy_id_required", message="policy.id must be a non-empty string", path="policy.id")
            )
            policy_obj = None
        elif not isinstance(pname, str) or not pname.strip():
            issues.append(
                ValidationIssue(code="policy_name_required", message="policy.name must be a non-empty string", path="policy.name")
            )
            policy_obj = None
        elif not isinstance(pver, str) or not pver.strip():
            issues.append(
                ValidationIssue(
                    code="policy_version_required", message="policy.version must be a non-empty string", path="policy.version"
                )
            )
            policy_obj = None
        else:
            policy_obj = PolicyModuleIdentity(id=pid.strip(), name=pname.strip(), version=pver.strip())

    reqs_raw = data.get("requirements")
    if not isinstance(reqs_raw, list) or len(reqs_raw) == 0:
        issues.append(
            ValidationIssue(
                code="requirements_required", message="requirements must be a non-empty array", path="requirements"
            )
        )
        reqs: list[PolicyModuleRequirement] = []
    else:
        reqs = []
        seen_codes: set[str] = set()
        for i, r in enumerate(reqs_raw):
            base = f"requirements[{i}]"
            if not isinstance(r, Mapping):
                issues.append(
                    ValidationIssue(code="requirement_invalid", message="each requirement must be an object", path=base)
                )
                continue
            code = r.get("code")
            if not isinstance(code, str) or not code.strip():
                issues.append(
                    ValidationIssue(code="requirement_code_required", message="code must be a non-empty string", path=f"{base}.code")
                )
                continue
            code_s = code.strip()
            if code_s in seen_codes:
                issues.append(
                    ValidationIssue(
                        code="requirement_code_duplicate", message=f"duplicate requirement code: {code_s}", path=f"{base}.code"
                    )
                )
                continue
            seen_codes.add(code_s)
            ev_raw = r.get("required_evidence")
            if not isinstance(ev_raw, list) or len(ev_raw) == 0:
                issues.append(
                    ValidationIssue(
                        code="required_evidence_required",
                        message="required_evidence must be a non-empty array of strings",
                        path=f"{base}.required_evidence",
                    )
                )
                continue
            ev_list: list[str] = []
            bad_ev = False
            for j, item in enumerate(ev_raw):
                if not isinstance(item, str) or not item.strip():
                    issues.append(
                        ValidationIssue(
                            code="required_evidence_item_invalid",
                            message="each required_evidence entry must be a non-empty string",
                            path=f"{base}.required_evidence[{j}]",
                        )
                    )
                    bad_ev = True
                    break
                ev_list.append(item.strip())
            if bad_ev:
                continue
            reqs.append(PolicyModuleRequirement(code=code_s, required_evidence=tuple(ev_list)))

    if isinstance(reqs_raw, list) and len(reqs_raw) > 0 and len(reqs) == 0:
        issues.append(
            ValidationIssue(
                code="requirements_all_invalid",
                message="no valid requirements could be parsed from the requirements array",
                path="requirements",
            )
        )

    if not isinstance(sv, str) or not sv.strip() or policy_obj is None or len(reqs) == 0:
        return None, tuple(sorted(issues, key=lambda x: (x.path, x.code, x.message)))

    doc = GovernancePolicyModuleDocument(
        schema_version=sv.strip(),
        policy=policy_obj,
        requirements=tuple(reqs),
    )
    return doc, tuple(sorted(issues, key=lambda x: (x.path, x.code, x.message)))


def _canonical_policy_module_payload(doc: GovernancePolicyModuleDocument) -> dict[str, Any]:
    reqs = sorted(doc.requirements, key=lambda r: r.code)
    return {
        "policy": {"id": doc.policy.id, "name": doc.policy.name, "version": doc.policy.version},
        "requirements": [{"code": r.code, "required_evidence": list(r.required_evidence)} for r in reqs],
        "schema_version": doc.schema_version,
    }


def canonical_governance_policy_module_document(doc: GovernancePolicyModuleDocument) -> dict[str, Any]:
    return _canonical_policy_module_payload(doc)


def digest_governance_policy_module_document(doc: GovernancePolicyModuleDocument) -> str:
    return canonical_digest(_canonical_policy_module_payload(doc))


def validate_governance_policy_module_document(data: Any) -> ValidationResult:
    doc, parse_issues = governance_policy_module_from_dict(data)
    issues = list(parse_issues)
    if doc is None:
        return ValidationResult(ok=False, issues=tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message))))

    expected_sv = "govai.standards.governance_policy_module.v1"
    if doc.schema_version != expected_sv:
        issues.append(
            ValidationIssue(
                code="schema_version_unsupported",
                message=f"schema_version must be exactly {expected_sv!r} for this interchange revision",
                path="schema_version",
            )
        )

    issues_sorted = tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))
    ok = len(issues_sorted) == 0
    d = digest_governance_policy_module_document(doc) if ok else None
    return ValidationResult(ok=ok, issues=issues_sorted, digest=d)
