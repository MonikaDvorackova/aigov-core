from __future__ import annotations

from dataclasses import fields

import pytest

from aigov_py.audit_export_manifest import (
    AuditExportManifest,
    AuditExportManifestItem,
    ManifestCompletenessSummary,
    ManifestEvidenceRef,
    build_audit_export_manifest,
)
from aigov_py.audit_exports import (
    AuditExportMode,
    AuditExportRequest,
    ControlEvidenceRequirement,
    EvidenceCompletenessStatus,
)


def _request() -> AuditExportRequest:
    return AuditExportRequest(
        tenant_id="tenant-1",
        mode=AuditExportMode.EVIDENCE_COMPLETENESS,
    )


def _requirements() -> tuple[ControlEvidenceRequirement, ...]:
    return (
        ControlEvidenceRequirement(
            control_id="control.complete",
            required_evidence_ref_ids=("evidence:a", "evidence:b"),
        ),
        ControlEvidenceRequirement(
            control_id="control.not_applicable",
            evidence_applicable=False,
            required_evidence_ref_ids=("evidence:would-not-matter",),
        ),
    )


def test_manifest_generated_with_stable_digest() -> None:
    manifest = build_audit_export_manifest(
        _request(),
        generated_at="2026-05-08T00:00:00Z",
        control_requirements=_requirements(),
        evidence_refs=("evidence:b", "evidence:a"),
        dataset_lineage_refs=("dataset:lineage-1",),
        override_refs=("override:approved-1",),
        ai_act_requirement_refs=("ai-act:annex-iii",),
    )

    assert manifest.manifest_schema_version == "audit-export-manifest.v1"
    assert manifest.tenant_id == "tenant-1"
    assert manifest.export_mode is AuditExportMode.EVIDENCE_COMPLETENESS
    assert manifest.manifest_digest.startswith("sha256:")
    assert len(manifest.manifest_digest) == len("sha256:") + 64
    assert manifest.completeness_summary == ManifestCompletenessSummary(
        total_controls=2,
        complete_controls=1,
        incomplete_controls=0,
        not_applicable_controls=1,
        incomplete_control_ids=(),
    )


def test_same_input_gives_same_digest() -> None:
    kwargs = {
        "generated_at": "2026-05-08T00:00:00Z",
        "control_requirements": _requirements(),
        "evidence_refs": ("evidence:b", "evidence:a"),
        "dataset_lineage_refs": ("dataset:lineage-1",),
        "override_refs": ("override:approved-1",),
        "ai_act_requirement_refs": ("ai-act:annex-iii",),
    }

    first = build_audit_export_manifest(_request(), **kwargs)
    second = build_audit_export_manifest(_request(), **kwargs)

    assert first == second
    assert first.manifest_digest == second.manifest_digest


def test_changed_evidence_refs_change_digest() -> None:
    base = build_audit_export_manifest(
        _request(),
        generated_at="2026-05-08T00:00:00Z",
        control_requirements=_requirements(),
        evidence_refs=("evidence:a", "evidence:b"),
    )
    changed = build_audit_export_manifest(
        _request(),
        generated_at="2026-05-08T00:00:00Z",
        control_requirements=_requirements(),
        evidence_refs=("evidence:a", "evidence:c"),
    )

    assert base.manifest_digest != changed.manifest_digest


def test_missing_evidence_marks_incomplete() -> None:
    manifest = build_audit_export_manifest(
        _request(),
        generated_at="2026-05-08T00:00:00Z",
        control_requirements=_requirements(),
        evidence_refs=("evidence:a",),
    )

    incomplete = manifest.controls[0]
    assert incomplete.control_id == "control.complete"
    assert incomplete.status is EvidenceCompletenessStatus.INCOMPLETE
    assert incomplete.missing_evidence_ref_ids == ("evidence:b",)
    assert manifest.completeness_summary.incomplete_control_ids == ("control.complete",)


def test_not_applicable_remains_not_applicable() -> None:
    manifest = build_audit_export_manifest(
        _request(),
        generated_at="2026-05-08T00:00:00Z",
        control_requirements=_requirements(),
        evidence_refs=(),
    )

    not_applicable = manifest.controls[1]
    assert not_applicable.control_id == "control.not_applicable"
    assert not_applicable.status is EvidenceCompletenessStatus.NOT_APPLICABLE
    assert not_applicable.missing_evidence_ref_ids == ()


def test_dataset_refs_copied_as_refs_only() -> None:
    manifest = build_audit_export_manifest(
        _request(),
        generated_at="2026-05-08T00:00:00Z",
        control_requirements=(),
        dataset_lineage_refs=(" dataset:2 ", "dataset:1", "dataset:1"),
    )

    assert manifest.dataset_lineage_refs == ("dataset:1", "dataset:2")


def test_override_refs_copied_as_refs_only() -> None:
    manifest = build_audit_export_manifest(
        _request(),
        generated_at="2026-05-08T00:00:00Z",
        control_requirements=(),
        override_refs=(" override:2 ", "override:1", "override:1"),
    )

    assert manifest.override_refs == ("override:1", "override:2")


def test_evidence_refs_are_opaque_ids_only() -> None:
    manifest = build_audit_export_manifest(
        _request(),
        generated_at="2026-05-08T00:00:00Z",
        control_requirements=(),
        evidence_refs=(ManifestEvidenceRef(ref_id=" evidence:2 "), "evidence:1"),
    )

    assert manifest.evidence_refs == (
        ManifestEvidenceRef(ref_id="evidence:1"),
        ManifestEvidenceRef(ref_id="evidence:2"),
    )


def test_missing_tenant_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="tenant_id is required"):
        build_audit_export_manifest(
            AuditExportRequest(
                tenant_id=" ",
                mode=AuditExportMode.EVIDENCE_COMPLETENESS,
            ),
            generated_at="2026-05-08T00:00:00Z",
            control_requirements=(),
        )


def test_export_mode_constrained_to_existing_enum() -> None:
    class _FakeMode:
        ...

    with pytest.raises(ValueError, match="export mode is required"):
        build_audit_export_manifest(
            AuditExportRequest(
                tenant_id="tenant-1",
                mode=_FakeMode(),  # type: ignore[arg-type]
            ),
            generated_at="2026-05-08T00:00:00Z",
            control_requirements=(),
        )


def test_no_raw_content_fields_are_modeled() -> None:
    banned_name_parts = (
        "body",
        "blob",
        "content",
        "payload",
        "prompt",
        "raw",
        "secret",
    )
    for cls in (
        AuditExportManifest,
        AuditExportManifestItem,
        ManifestCompletenessSummary,
        ManifestEvidenceRef,
    ):
        for f in fields(cls):
            low = f.name.lower()
            for part in banned_name_parts:
                assert part not in low, f"{cls.__name__}.{f.name}"
