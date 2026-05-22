from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone

from aigov_py.audit_exports import (
    AuditExportMode,
    AuditExportRequest,
    ControlEvidenceRequirement,
    ControlEvidenceResult,
    EvidenceCompletenessStatus,
    TimeRange,
    evaluate_evidence_completeness,
    validate_audit_export_request,
)


def test_valid_export_request_passes() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 6, 1, tzinfo=timezone.utc)
    req = AuditExportRequest(
        tenant_id="tenant-1",
        mode=AuditExportMode.AIACT_READINESS,
        time_range=TimeRange(start=start, end=end),
        control_ids=("c-001", "c-002"),
    )
    assert validate_audit_export_request(req) == ()


def test_missing_tenant_id_fails() -> None:
    req = AuditExportRequest(tenant_id="   ", mode=AuditExportMode.EVIDENCE_COMPLETENESS)
    errs = validate_audit_export_request(req)
    assert errs
    assert "tenant_id is required and must be non-empty" in errs


class _FakeMode:
    """Not an AuditExportMode; violates the contract for negative testing only."""

    ...


def test_invalid_mode_fails() -> None:
    req = AuditExportRequest(
        tenant_id="tenant-1",
        mode=_FakeMode(),  # type: ignore[arg-type]
    )
    errs = validate_audit_export_request(req)
    assert errs
    assert (
        "export mode is required and must be a member of AuditExportMode"
        in errs
    )


def test_invalid_time_range_fails() -> None:
    start = datetime(2026, 6, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, tzinfo=timezone.utc)
    req = AuditExportRequest(
        tenant_id="tenant-1",
        mode=AuditExportMode.FULL_IMMUTABLE_PACKAGE,
        time_range=TimeRange(start=start, end=end),
    )
    errs = validate_audit_export_request(req)
    assert errs
    assert (
        "time_range if present must satisfy start <= end with comparable datetimes"
        in errs
    )


def test_mixed_tz_time_range_fails() -> None:
    start_naive = datetime(2026, 1, 1)
    end_aware = datetime(2026, 6, 1, tzinfo=timezone.utc)
    req = AuditExportRequest(
        tenant_id="tenant-1",
        mode=AuditExportMode.AIACT_READINESS,
        time_range=TimeRange(start=start_naive, end=end_aware),
    )
    errs = validate_audit_export_request(req)
    assert errs
    assert (
        "time_range start and end must both be naive or both timezone-aware datetimes"
        in errs
    )


def test_empty_control_ids_tuple_when_present_fails() -> None:
    req = AuditExportRequest(
        tenant_id="tenant-1",
        mode=AuditExportMode.EVIDENCE_COMPLETENESS,
        control_ids=(),
    )
    errs = validate_audit_export_request(req)
    assert errs
    assert (
        "control_ids if present must contain at least one non-empty identifier"
        in errs
    )


def test_empty_control_id_element_fails() -> None:
    req = AuditExportRequest(
        tenant_id="tenant-1",
        mode=AuditExportMode.EVIDENCE_COMPLETENESS,
        control_ids=("ok", " "),
    )
    errs = validate_audit_export_request(req)
    assert errs
    assert (
        "control_ids if present must contain only non-empty strings after stripping"
        in errs
    )


def test_complete_evidence_returns_complete() -> None:
    ce = ControlEvidenceRequirement(
        control_id="c-001",
        required_evidence_ref_ids=("artifact:run-digest", "ref:dataset-lineage-key"),
    )
    res = evaluate_evidence_completeness(
        ce,
        present_evidence_ref_ids=(
            "ref:dataset-lineage-key",
            "artifact:run-digest",
            "extra:opaque-key",
        ),
    )
    assert res.control_id == "c-001"
    assert res.status is EvidenceCompletenessStatus.COMPLETE


def test_missing_evidence_returns_incomplete() -> None:
    ce = ControlEvidenceRequirement(
        control_id="c-002",
        required_evidence_ref_ids=("artifact:run-digest", "ref:policy-bundle"),
    )
    res = evaluate_evidence_completeness(
        ce,
        present_evidence_ref_ids=("artifact:run-digest",),
    )
    assert res.status is EvidenceCompletenessStatus.INCOMPLETE


def test_not_applicable_returns_not_applicable() -> None:
    ce = ControlEvidenceRequirement(
        control_id="c-099",
        evidence_applicable=False,
        required_evidence_ref_ids=("artifact:would-matter-if-applicable",),
    )
    res = evaluate_evidence_completeness(
        ce,
        present_evidence_ref_ids=(),
    )
    assert res.status is EvidenceCompletenessStatus.NOT_APPLICABLE


def test_deterministic_repeated_evaluation() -> None:
    ce = ControlEvidenceRequirement(
        control_id=" c-007 ",
        required_evidence_ref_ids=("  ref-a  ", "ref-b"),
    )
    present = (" ref-b ", " ref-a ")
    once = evaluate_evidence_completeness(ce, present_evidence_ref_ids=present)
    twice = evaluate_evidence_completeness(ce, present_evidence_ref_ids=present)
    assert once == twice
    assert once.control_id == "c-007"
    assert once.status is EvidenceCompletenessStatus.COMPLETE


def test_deterministic_repeated_validate_request() -> None:
    req = AuditExportRequest(
        tenant_id="tenant-z",
        mode=AuditExportMode.EVIDENCE_COMPLETENESS,
    )
    assert validate_audit_export_request(req) == validate_audit_export_request(req)


def test_no_raw_content_fields_are_modeled() -> None:
    banned_name_parts = ("body", "content", "payload", "blob", "secret", "raw")
    for cls in (
        AuditExportRequest,
        ControlEvidenceRequirement,
        ControlEvidenceResult,
        TimeRange,
    ):
        for f in fields(cls):
            low = f.name.lower()
            for part in banned_name_parts:
                assert part not in low, f"{cls.__name__}.{f.name}"
