from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AuditExportMode(Enum):
    EVIDENCE_COMPLETENESS = "EVIDENCE_COMPLETENESS"
    AIACT_READINESS = "AIACT_READINESS"
    FULL_IMMUTABLE_PACKAGE = "FULL_IMMUTABLE_PACKAGE"


class EvidenceCompletenessStatus(Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class TimeRange:
    """Inclusive-ish planning window: start instant must not be after end instant."""

    start: datetime
    end: datetime


@dataclass(frozen=True)
class AuditExportRequest:
    """Planning input for audit export bundles; carries only identifiers and mode — no payloads."""

    tenant_id: str
    mode: AuditExportMode
    time_range: TimeRange | None = None
    control_ids: tuple[str, ...] | None = None


@dataclass(frozen=True)
class ControlEvidenceRequirement:
    """Evidence refs are opaque identifiers (types, hashes, artifact keys) — never raw user content."""

    control_id: str
    evidence_applicable: bool = True
    required_evidence_ref_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ControlEvidenceResult:
    control_id: str
    status: EvidenceCompletenessStatus


_ERR_CONTROL_ID_EACH_NONEMPTY = (
    "control_ids if present must contain only non-empty strings after stripping"
)
_ERR_CONTROL_IDS_EMPTY_WHEN_PRESENT = (
    "control_ids if present must contain at least one non-empty identifier"
)
_ERR_MODE_REQUIRED = (
    "export mode is required and must be a member of AuditExportMode"
)
_ERR_TENANT_ID_REQUIRED = "tenant_id is required and must be non-empty"
_ERR_TIME_RANGE_ORDER = (
    "time_range if present must satisfy start <= end with comparable datetimes"
)
_ERR_TIME_ZONE_MIXED = (
    "time_range start and end must both be naive or both timezone-aware datetimes"
)


def _normalized_ref_set(refs: Collection[str]) -> frozenset[str]:
    out: set[str] = set()
    for r in refs:
        s = (r or "").strip()
        if s:
            out.add(s)
    return frozenset(out)


def validate_audit_export_request(request: AuditExportRequest) -> tuple[str, ...]:
    """Return sorted, deterministic error messages; empty tuple means valid."""
    errors: list[str] = []

    if not isinstance(request.mode, AuditExportMode):
        errors.append(_ERR_MODE_REQUIRED)

    if not (request.tenant_id or "").strip():
        errors.append(_ERR_TENANT_ID_REQUIRED)

    tr = request.time_range
    if tr is not None:
        a, b = tr.start, tr.end
        naive_a = getattr(a, "tzinfo", None) is None
        naive_b = getattr(b, "tzinfo", None) is None
        if naive_a != naive_b:
            errors.append(_ERR_TIME_ZONE_MIXED)
        else:
            try:
                if not (a <= b):
                    errors.append(_ERR_TIME_RANGE_ORDER)
            except TypeError:
                errors.append(_ERR_TIME_RANGE_ORDER)

    cids = request.control_ids
    if cids is not None:
        if len(cids) == 0:
            errors.append(_ERR_CONTROL_IDS_EMPTY_WHEN_PRESENT)
        for cid in cids:
            if not (cid or "").strip():
                errors.append(_ERR_CONTROL_ID_EACH_NONEMPTY)
                break

    return tuple(sorted(errors))


def evaluate_evidence_completeness(
    requirement: ControlEvidenceRequirement,
    *,
    present_evidence_ref_ids: Collection[str],
) -> ControlEvidenceResult:
    """Deterministic per-control evidence completeness; planning only — no side effects."""
    cid = (requirement.control_id or "").strip()
    if not cid:
        cid = ""

    if not requirement.evidence_applicable:
        return ControlEvidenceResult(control_id=cid, status=EvidenceCompletenessStatus.NOT_APPLICABLE)

    required_f = _normalized_ref_set(requirement.required_evidence_ref_ids)
    present_f = _normalized_ref_set(present_evidence_ref_ids)

    if required_f.issubset(present_f):
        return ControlEvidenceResult(control_id=cid, status=EvidenceCompletenessStatus.COMPLETE)

    return ControlEvidenceResult(control_id=cid, status=EvidenceCompletenessStatus.INCOMPLETE)
