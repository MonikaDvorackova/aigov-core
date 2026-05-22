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


class TraceVerificationStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class TraceVerificationRequirement:
    requirement_id: str
    description: str


@dataclass(frozen=True)
class TraceVerificationFinding:
    finding_id: str
    requirement_id: str
    status: TraceVerificationStatus


@dataclass(frozen=True)
class TraceVerificationPlanDocument:
    schema_version: str
    trace_id: str
    tenant_scope: str
    requirements: tuple[TraceVerificationRequirement, ...]
    findings: tuple[TraceVerificationFinding, ...]
    plan_digest: str | None


def _parse_req(raw: Any, idx: int, issues: list[ValidationIssue]) -> TraceVerificationRequirement | None:
    base = f"requirements[{idx}]"
    if not isinstance(raw, Mapping):
        issues.append(
            ValidationIssue(
                code="requirement_invalid",
                message="each requirement must be an object",
                path=base,
            )
        )
        return None
    rid = raw.get("requirement_id")
    if not isinstance(rid, str) or not rid.strip():
        issues.append(
            ValidationIssue(
                code="requirement_id_required",
                message="requirement_id is required",
                path=f"{base}.requirement_id",
            )
        )
        return None
    desc = raw.get("description", "")
    if desc is None:
        desc = ""
    if not isinstance(desc, str):
        issues.append(
            ValidationIssue(
                code="description_invalid",
                message="description must be a string",
                path=f"{base}.description",
            )
        )
        return None
    return TraceVerificationRequirement(
        requirement_id=rid.strip(),
        description=desc,
    )


def _parse_finding(raw: Any, idx: int, issues: list[ValidationIssue]) -> TraceVerificationFinding | None:
    base = f"findings[{idx}]"
    if not isinstance(raw, Mapping):
        issues.append(
            ValidationIssue(
                code="finding_invalid",
                message="each finding must be an object",
                path=base,
            )
        )
        return None
    fid = raw.get("finding_id")
    if not isinstance(fid, str) or not fid.strip():
        issues.append(
            ValidationIssue(
                code="finding_id_required",
                message="finding_id is required",
                path=f"{base}.finding_id",
            )
        )
        return None
    rid = raw.get("requirement_id")
    if not isinstance(rid, str) or not rid.strip():
        issues.append(
            ValidationIssue(
                code="finding_requirement_required",
                message="requirement_id is required on each finding",
                path=f"{base}.requirement_id",
            )
        )
        return None
    st_raw = raw.get("status")
    st: TraceVerificationStatus | None = None
    if isinstance(st_raw, str):
        try:
            st = TraceVerificationStatus(st_raw.strip())
        except ValueError:
            issues.append(
                ValidationIssue(
                    code="status_invalid",
                    message="status must be PASS, WARN, FAIL, or NOT_APPLICABLE",
                    path=f"{base}.status",
                )
            )
    else:
        issues.append(
            ValidationIssue(
                code="status_invalid",
                message="status must be a string",
                path=f"{base}.status",
            )
        )
    if st is None:
        return None
    return TraceVerificationFinding(
        finding_id=fid.strip(),
        requirement_id=rid.strip(),
        status=st,
    )


def trace_verification_plan_document_from_dict(
    data: Any,
) -> tuple[TraceVerificationPlanDocument | None, tuple[ValidationIssue, ...]]:
    issues: list[ValidationIssue] = []
    if not isinstance(data, Mapping):
        return None, (ValidationIssue(code="root_invalid", message="document root must be an object", path=""),)

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

    tid = data.get("trace_id")
    if not isinstance(tid, str) or not tid.strip():
        issues.append(
            ValidationIssue(
                code="trace_id_required",
                message="trace_id is required",
                path="trace_id",
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

    req_raw = data.get("requirements", [])
    if not isinstance(req_raw, list):
        issues.append(
            ValidationIssue(
                code="requirements_invalid",
                message="requirements must be an array",
                path="requirements",
            )
        )
        req_raw = []

    reqs: list[TraceVerificationRequirement] = []
    seen_req: set[str] = set()
    for i, raw in enumerate(req_raw):
        r = _parse_req(raw, i, issues)
        if r is None:
            continue
        if r.requirement_id in seen_req:
            issues.append(
                ValidationIssue(
                    code="requirement_id_duplicate",
                    message=f"duplicate requirement_id: {r.requirement_id}",
                    path=f"requirements[{i}].requirement_id",
                )
            )
            continue
        seen_req.add(r.requirement_id)
        reqs.append(r)

    fin_raw = data.get("findings", [])
    if not isinstance(fin_raw, list):
        issues.append(
            ValidationIssue(
                code="findings_invalid",
                message="findings must be an array",
                path="findings",
            )
        )
        fin_raw = []

    fins: list[TraceVerificationFinding] = []
    seen_fin: set[str] = set()
    for i, raw in enumerate(fin_raw):
        f = _parse_finding(raw, i, issues)
        if f is None:
            continue
        if f.finding_id in seen_fin:
            issues.append(
                ValidationIssue(
                    code="finding_id_duplicate",
                    message=f"duplicate finding_id: {f.finding_id}",
                    path=f"findings[{i}].finding_id",
                )
            )
            continue
        seen_fin.add(f.finding_id)
        fins.append(f)

    plan_digest_raw = data.get("plan_digest")
    plan_digest: str | None = None
    if plan_digest_raw is not None:
        if isinstance(plan_digest_raw, str) and plan_digest_raw.strip():
            plan_digest = plan_digest_raw.strip()
        else:
            issues.append(
                ValidationIssue(
                    code="plan_digest_invalid",
                    message="plan_digest must be a non-empty string when present",
                    path="plan_digest",
                )
            )

    if not isinstance(sv, str) or not sv.strip():
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))
    if not isinstance(tid, str) or not tid.strip():
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))
    if not isinstance(ts, str) or not ts.strip():
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))

    doc = TraceVerificationPlanDocument(
        schema_version=sv.strip(),
        trace_id=tid.strip(),
        tenant_scope=ts.strip(),
        requirements=tuple(reqs),
        findings=tuple(fins),
        plan_digest=plan_digest,
    )
    return doc, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))


def _canonical_trace_plan_payload(doc: TraceVerificationPlanDocument) -> dict[str, Any]:
    """Canonical preimage for plan_digest (excludes plan_digest)."""
    reqs = sorted(doc.requirements, key=lambda r: r.requirement_id)
    fins = sorted(doc.findings, key=lambda f: (f.finding_id,))
    return {
        "findings": [
            {
                "finding_id": f.finding_id,
                "requirement_id": f.requirement_id,
                "status": f.status.value,
            }
            for f in fins
        ],
        "requirements": [
            {
                "description": r.description,
                "requirement_id": r.requirement_id,
            }
            for r in reqs
        ],
        "schema_version": doc.schema_version,
        "tenant_scope": doc.tenant_scope,
        "trace_id": doc.trace_id,
    }


def canonical_trace_verification_plan_document(doc: TraceVerificationPlanDocument) -> dict[str, Any]:
    payload = _canonical_trace_plan_payload(doc)
    out = dict(payload)
    out["plan_digest"] = canonical_digest(payload)
    return out


def digest_trace_verification_plan_document(doc: TraceVerificationPlanDocument) -> str:
    return canonical_digest(_canonical_trace_plan_payload(doc))


def validate_trace_verification_plan_document(data: Any) -> ValidationResult:
    doc, parse_issues = trace_verification_plan_document_from_dict(data)
    issues = list(parse_issues)
    if doc is None:
        return ValidationResult(ok=False, issues=tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message))))

    req_ids = {r.requirement_id for r in doc.requirements}
    computed = digest_trace_verification_plan_document(doc)
    if doc.plan_digest is not None and doc.plan_digest != computed:
        issues.append(
            ValidationIssue(
                code="plan_digest_mismatch",
                message="plan_digest does not match canonical digest of plan fields",
                path="plan_digest",
            )
        )

    for i, f in enumerate(doc.findings):
        if f.requirement_id not in req_ids:
            issues.append(
                ValidationIssue(
                    code="finding_requirement_unresolved",
                    message=f"finding references unknown requirement_id: {f.requirement_id}",
                    path=f"findings[{i}].requirement_id",
                )
            )

    issues_sorted = tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))
    ok = len(issues_sorted) == 0
    d = computed if ok else None
    return ValidationResult(ok=ok, issues=issues_sorted, digest=d)
