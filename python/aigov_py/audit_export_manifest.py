from __future__ import annotations

import hashlib
from collections.abc import Collection
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from aigov_py.audit_exports import (
    AuditExportMode,
    AuditExportRequest,
    ControlEvidenceRequirement,
    EvidenceCompletenessStatus,
    evaluate_evidence_completeness,
    validate_audit_export_request,
)
from aigov_py.canonical_json import canonical_bytes


MANIFEST_SCHEMA_VERSION = "audit-export-manifest.v1"


@dataclass(frozen=True)
class ManifestEvidenceRef:
    """Opaque evidence identifier used for manifest planning; never carries payloads."""

    ref_id: str


@dataclass(frozen=True)
class AuditExportManifestItem:
    control_id: str
    status: EvidenceCompletenessStatus
    required_evidence_ref_ids: tuple[str, ...] = ()
    present_evidence_ref_ids: tuple[str, ...] = ()
    missing_evidence_ref_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ManifestCompletenessSummary:
    total_controls: int
    complete_controls: int
    incomplete_controls: int
    not_applicable_controls: int
    incomplete_control_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class AuditExportManifest:
    manifest_schema_version: str
    tenant_id: str
    export_mode: AuditExportMode
    generated_at: str
    controls: tuple[AuditExportManifestItem, ...]
    evidence_refs: tuple[ManifestEvidenceRef, ...]
    dataset_lineage_refs: tuple[str, ...]
    override_refs: tuple[str, ...]
    ai_act_requirement_refs: tuple[str, ...]
    completeness_summary: ManifestCompletenessSummary
    manifest_digest: str


def _norm(value: str) -> str:
    return (value or "").strip()


def _normalized_unique(values: Collection[str]) -> tuple[str, ...]:
    return tuple(sorted({_norm(v) for v in values if _norm(v)}))


def _normalize_generated_at(generated_at: datetime | str) -> str:
    if isinstance(generated_at, datetime):
        if generated_at.tzinfo is None:
            return generated_at.isoformat()
        return generated_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return _norm(generated_at)


def _manifest_evidence_ref_ids(
    evidence_refs: Collection[ManifestEvidenceRef | str],
) -> tuple[str, ...]:
    out: list[str] = []
    for ref in evidence_refs:
        if isinstance(ref, ManifestEvidenceRef):
            out.append(ref.ref_id)
        else:
            out.append(ref)
    return _normalized_unique(out)


def _manifest_evidence_refs(
    evidence_refs: Collection[ManifestEvidenceRef | str],
) -> tuple[ManifestEvidenceRef, ...]:
    return tuple(ManifestEvidenceRef(ref_id=ref_id) for ref_id in _manifest_evidence_ref_ids(evidence_refs))


def _filtered_requirements(
    request: AuditExportRequest,
    requirements: Collection[ControlEvidenceRequirement],
) -> tuple[ControlEvidenceRequirement, ...]:
    allowed = None
    if request.control_ids is not None:
        allowed = set(_normalized_unique(request.control_ids))

    out: list[ControlEvidenceRequirement] = []
    for req in requirements:
        cid = _norm(req.control_id)
        if allowed is not None and cid not in allowed:
            continue
        out.append(req)

    return tuple(sorted(out, key=lambda r: _norm(r.control_id)))


def _manifest_item(
    requirement: ControlEvidenceRequirement,
    *,
    present_ref_ids: tuple[str, ...],
) -> AuditExportManifestItem:
    result = evaluate_evidence_completeness(
        requirement,
        present_evidence_ref_ids=present_ref_ids,
    )
    required = _normalized_unique(requirement.required_evidence_ref_ids)
    present = tuple(ref for ref in required if ref in set(present_ref_ids))
    missing = tuple(ref for ref in required if ref not in set(present_ref_ids))
    if result.status is EvidenceCompletenessStatus.NOT_APPLICABLE:
        missing = ()

    return AuditExportManifestItem(
        control_id=_norm(result.control_id),
        status=result.status,
        required_evidence_ref_ids=required,
        present_evidence_ref_ids=present,
        missing_evidence_ref_ids=missing,
    )


def _completeness_summary(
    controls: tuple[AuditExportManifestItem, ...],
) -> ManifestCompletenessSummary:
    complete = tuple(c for c in controls if c.status is EvidenceCompletenessStatus.COMPLETE)
    incomplete = tuple(c for c in controls if c.status is EvidenceCompletenessStatus.INCOMPLETE)
    not_applicable = tuple(
        c for c in controls if c.status is EvidenceCompletenessStatus.NOT_APPLICABLE
    )
    return ManifestCompletenessSummary(
        total_controls=len(controls),
        complete_controls=len(complete),
        incomplete_controls=len(incomplete),
        not_applicable_controls=len(not_applicable),
        incomplete_control_ids=tuple(c.control_id for c in incomplete),
    )


def _enum_value(value: Any) -> Any:
    if isinstance(value, (AuditExportMode, EvidenceCompletenessStatus)):
        return value.value
    return value


def _canonical_manifest_payload(manifest: AuditExportManifest) -> dict[str, Any]:
    return {
        "manifest_schema_version": manifest.manifest_schema_version,
        "tenant_id": manifest.tenant_id,
        "export_mode": _enum_value(manifest.export_mode),
        "generated_at": manifest.generated_at,
        "controls": [
            {
                "control_id": item.control_id,
                "status": _enum_value(item.status),
                "required_evidence_ref_ids": list(item.required_evidence_ref_ids),
                "present_evidence_ref_ids": list(item.present_evidence_ref_ids),
                "missing_evidence_ref_ids": list(item.missing_evidence_ref_ids),
            }
            for item in manifest.controls
        ],
        "evidence_refs": [{"ref_id": ref.ref_id} for ref in manifest.evidence_refs],
        "dataset_lineage_refs": list(manifest.dataset_lineage_refs),
        "override_refs": list(manifest.override_refs),
        "ai_act_requirement_refs": list(manifest.ai_act_requirement_refs),
        "completeness_summary": {
            "total_controls": manifest.completeness_summary.total_controls,
            "complete_controls": manifest.completeness_summary.complete_controls,
            "incomplete_controls": manifest.completeness_summary.incomplete_controls,
            "not_applicable_controls": manifest.completeness_summary.not_applicable_controls,
            "incomplete_control_ids": list(
                manifest.completeness_summary.incomplete_control_ids
            ),
        },
    }


def manifest_digest(manifest: AuditExportManifest) -> str:
    """Digest canonical manifest fields, excluding the digest field itself."""
    return "sha256:" + hashlib.sha256(
        canonical_bytes(_canonical_manifest_payload(manifest))
    ).hexdigest()


def build_audit_export_manifest(
    request: AuditExportRequest,
    *,
    generated_at: datetime | str,
    control_requirements: Collection[ControlEvidenceRequirement],
    evidence_refs: Collection[ManifestEvidenceRef | str] = (),
    dataset_lineage_refs: Collection[str] = (),
    override_refs: Collection[str] = (),
    ai_act_requirement_refs: Collection[str] = (),
    manifest_schema_version: str = MANIFEST_SCHEMA_VERSION,
) -> AuditExportManifest:
    """Build a deterministic in-memory manifest plan; no I/O, ledger, or HTTP wiring."""
    errors = validate_audit_export_request(request)
    if errors:
        raise ValueError("; ".join(errors))

    evidence = _manifest_evidence_refs(evidence_refs)
    evidence_ref_ids = tuple(ref.ref_id for ref in evidence)
    controls = tuple(
        _manifest_item(requirement, present_ref_ids=evidence_ref_ids)
        for requirement in _filtered_requirements(request, control_requirements)
    )

    manifest = AuditExportManifest(
        manifest_schema_version=_norm(manifest_schema_version),
        tenant_id=_norm(request.tenant_id),
        export_mode=request.mode,
        generated_at=_normalize_generated_at(generated_at),
        controls=controls,
        evidence_refs=evidence,
        dataset_lineage_refs=_normalized_unique(dataset_lineage_refs),
        override_refs=_normalized_unique(override_refs),
        ai_act_requirement_refs=_normalized_unique(ai_act_requirement_refs),
        completeness_summary=_completeness_summary(controls),
        manifest_digest="",
    )
    return replace(manifest, manifest_digest=manifest_digest(manifest))
