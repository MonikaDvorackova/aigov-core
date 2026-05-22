from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from aigov_py.standards.common import (
    ValidationIssue,
    ValidationResult,
    canonical_digest,
    find_raw_content_fields,
    normalize_digest_token,
    validate_digest_token,
)


class EvidencePackEvidenceType(str, Enum):
    """GOVERNED artifacts must include non-empty control_refs."""

    GOVERNED = "GOVERNED"
    REFERENCE = "REFERENCE"


@dataclass(frozen=True)
class EvidencePackDigestManifestEntry:
    artifact_id: str
    content_digest: str


@dataclass(frozen=True)
class EvidencePackDigestManifest:
    entries: tuple[EvidencePackDigestManifestEntry, ...]


@dataclass(frozen=True)
class EvidencePackArtifactRef:
    artifact_id: str
    artifact_type: str
    uri: str | None
    content_digest: str
    evidence_type: EvidencePackEvidenceType
    control_refs: tuple[str, ...]
    ai_act_refs: tuple[str, ...]


@dataclass(frozen=True)
class GovernanceEvidencePackDocument:
    schema_version: str
    pack_id: str
    tenant_scope: str
    run_id: str | None
    artifacts: tuple[EvidencePackArtifactRef, ...]
    digest_manifest: EvidencePackDigestManifest
    pack_digest: str | None


def _parse_manifest(data: Any, issues: list[ValidationIssue]) -> EvidencePackDigestManifest | None:
    if not isinstance(data, Mapping):
        issues.append(
            ValidationIssue(
                code="digest_manifest_invalid",
                message="digest_manifest must be an object",
                path="digest_manifest",
            )
        )
        return None
    ent_raw = data.get("entries", [])
    if not isinstance(ent_raw, list):
        issues.append(
            ValidationIssue(
                code="digest_manifest_entries_invalid",
                message="digest_manifest.entries must be an array",
                path="digest_manifest.entries",
            )
        )
        return None
    entries: list[EvidencePackDigestManifestEntry] = []
    for i, e in enumerate(ent_raw):
        p = f"digest_manifest.entries[{i}]"
        if not isinstance(e, Mapping):
            issues.append(
                ValidationIssue(
                    code="manifest_entry_invalid",
                    message="each manifest entry must be an object",
                    path=p,
                )
            )
            continue
        aid = e.get("artifact_id")
        cd = e.get("content_digest")
        if not isinstance(aid, str) or not aid.strip():
            issues.append(
                ValidationIssue(
                    code="manifest_artifact_id_required",
                    message="artifact_id is required",
                    path=f"{p}.artifact_id",
                )
            )
            continue
        if not isinstance(cd, str) or not validate_digest_token(cd):
            issues.append(
                ValidationIssue(
                    code="manifest_digest_invalid",
                    message="content_digest must be a valid digest token",
                    path=f"{p}.content_digest",
                )
            )
            continue
        try:
            norm = normalize_digest_token(cd)
        except ValueError:
            issues.append(
                ValidationIssue(
                    code="manifest_digest_invalid",
                    message="content_digest must be a valid digest token",
                    path=f"{p}.content_digest",
                )
            )
            continue
        entries.append(EvidencePackDigestManifestEntry(artifact_id=aid.strip(), content_digest=norm))
    return EvidencePackDigestManifest(entries=tuple(entries))


def _parse_artifact(raw: Any, idx: int, issues: list[ValidationIssue]) -> EvidencePackArtifactRef | None:
    base = f"artifacts[{idx}]"
    if not isinstance(raw, Mapping):
        issues.append(
            ValidationIssue(
                code="artifact_invalid",
                message="each artifact must be an object",
                path=base,
            )
        )
        return None
    aid = raw.get("artifact_id")
    if not isinstance(aid, str) or not aid.strip():
        issues.append(
            ValidationIssue(
                code="artifact_id_required",
                message="artifact_id is required",
                path=f"{base}.artifact_id",
            )
        )
        return None
    at = raw.get("artifact_type")
    if not isinstance(at, str) or not at.strip():
        issues.append(
            ValidationIssue(
                code="artifact_type_required",
                message="artifact_type is required",
                path=f"{base}.artifact_type",
            )
        )
        return None
    uri = raw.get("uri")
    if uri is not None and (not isinstance(uri, str) or not uri.strip()):
        issues.append(
            ValidationIssue(
                code="uri_invalid",
                message="uri must be a non-empty string when present",
                path=f"{base}.uri",
            )
        )
        uri = None
    cd = raw.get("content_digest")
    if not isinstance(cd, str) or not validate_digest_token(cd):
        issues.append(
            ValidationIssue(
                code="content_digest_invalid",
                message="content_digest must be a valid digest token (64 hex or sha256:<hex>)",
                path=f"{base}.content_digest",
            )
        )
        return None
    try:
        norm_digest = normalize_digest_token(cd)
    except ValueError:
        issues.append(
            ValidationIssue(
                code="content_digest_invalid",
                message="content_digest must be a valid digest token",
                path=f"{base}.content_digest",
            )
        )
        return None

    et_raw = raw.get("evidence_type")
    et: EvidencePackEvidenceType | None = None
    if isinstance(et_raw, str):
        try:
            et = EvidencePackEvidenceType(et_raw.strip())
        except ValueError:
            issues.append(
                ValidationIssue(
                    code="evidence_type_invalid",
                    message="evidence_type must be GOVERNED or REFERENCE",
                    path=f"{base}.evidence_type",
                )
            )
    else:
        issues.append(
            ValidationIssue(
                code="evidence_type_invalid",
                message="evidence_type must be a string",
                path=f"{base}.evidence_type",
            )
        )

    cr_raw = raw.get("control_refs", [])
    if cr_raw is None:
        cr_raw = []
    control_refs: list[str] = []
    if not isinstance(cr_raw, list):
        issues.append(
            ValidationIssue(
                code="control_refs_invalid",
                message="control_refs must be an array of strings",
                path=f"{base}.control_refs",
            )
        )
    else:
        for j, c in enumerate(cr_raw):
            if not isinstance(c, str) or not c.strip():
                issues.append(
                    ValidationIssue(
                        code="control_ref_empty",
                        message="each control_refs entry must be a non-empty string",
                        path=f"{base}.control_refs[{j}]",
                    )
                )
            else:
                control_refs.append(c.strip())

    ai_raw = raw.get("ai_act_refs", [])
    if ai_raw is None:
        ai_raw = []
    ai_refs: list[str] = []
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

    if et is None:
        return None

    return EvidencePackArtifactRef(
        artifact_id=aid.strip(),
        artifact_type=at.strip(),
        uri=None if uri is None else str(uri).strip(),
        content_digest=norm_digest,
        evidence_type=et,
        control_refs=tuple(control_refs),
        ai_act_refs=tuple(ai_refs),
    )


def governance_evidence_pack_document_from_dict(
    data: Any,
) -> tuple[GovernanceEvidencePackDocument | None, tuple[ValidationIssue, ...]]:
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

    pid = data.get("pack_id")
    if not isinstance(pid, str) or not pid.strip():
        issues.append(
            ValidationIssue(
                code="pack_id_required",
                message="pack_id is required",
                path="pack_id",
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

    run_id = data.get("run_id")
    if run_id is not None:
        if not isinstance(run_id, str) or not run_id.strip():
            issues.append(
                ValidationIssue(
                    code="run_id_invalid",
                    message="run_id must be a non-empty string when present",
                    path="run_id",
                )
            )
            run_id = None
        else:
            run_id = run_id.strip()

    arts_raw = data.get("artifacts")
    if not isinstance(arts_raw, list) or len(arts_raw) == 0:
        issues.append(
            ValidationIssue(
                code="artifacts_required",
                message="artifacts must be a non-empty array",
                path="artifacts",
            )
        )
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))

    manifest = _parse_manifest(data.get("digest_manifest"), issues)
    if manifest is None and "digest_manifest" not in data:
        issues.append(
            ValidationIssue(
                code="digest_manifest_required",
                message="digest_manifest is required",
                path="digest_manifest",
            )
        )
    if manifest is None:
        manifest = EvidencePackDigestManifest(entries=())

    arts: list[EvidencePackArtifactRef] = []
    seen_aid: set[str] = set()
    for i, raw in enumerate(arts_raw):
        a = _parse_artifact(raw, i, issues)
        if a is None:
            continue
        if a.artifact_id in seen_aid:
            issues.append(
                ValidationIssue(
                    code="artifact_id_duplicate",
                    message=f"duplicate artifact_id: {a.artifact_id}",
                    path=f"artifacts[{i}].artifact_id",
                )
            )
            continue
        seen_aid.add(a.artifact_id)
        arts.append(a)

    pack_digest_raw = data.get("pack_digest")
    pack_digest: str | None = None
    if pack_digest_raw is not None:
        if isinstance(pack_digest_raw, str) and pack_digest_raw.strip():
            pack_digest = pack_digest_raw.strip()
        else:
            issues.append(
                ValidationIssue(
                    code="pack_digest_invalid",
                    message="pack_digest must be a non-empty string when present",
                    path="pack_digest",
                )
            )

    if not isinstance(sv, str) or not sv.strip():
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))
    if not isinstance(pid, str) or not pid.strip():
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))
    if not isinstance(ts, str) or not ts.strip():
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))

    doc = GovernanceEvidencePackDocument(
        schema_version=sv.strip(),
        pack_id=pid.strip(),
        tenant_scope=ts.strip(),
        run_id=run_id,
        artifacts=tuple(arts),
        digest_manifest=manifest,
        pack_digest=pack_digest,
    )
    return doc, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))


def canonical_digest_manifest(manifest: EvidencePackDigestManifest) -> dict[str, Any]:
    ents = sorted(manifest.entries, key=lambda e: (e.artifact_id, e.content_digest))
    return {
        "entries": [
            {"artifact_id": e.artifact_id, "content_digest": e.content_digest} for e in ents
        ]
    }


def _canonical_pack_payload(doc: GovernanceEvidencePackDocument) -> dict[str, Any]:
    arts = sorted(doc.artifacts, key=lambda a: a.artifact_id)
    return {
        "artifacts": [
            {
                "ai_act_refs": list(a.ai_act_refs),
                "artifact_id": a.artifact_id,
                "artifact_type": a.artifact_type,
                "content_digest": a.content_digest,
                "control_refs": list(a.control_refs),
                "evidence_type": a.evidence_type.value,
                "uri": a.uri,
            }
            for a in arts
        ],
        "digest_manifest": canonical_digest_manifest(doc.digest_manifest),
        "pack_id": doc.pack_id,
        "run_id": doc.run_id,
        "schema_version": doc.schema_version,
        "tenant_scope": doc.tenant_scope,
    }


def canonical_governance_evidence_pack_document(doc: GovernanceEvidencePackDocument) -> dict[str, Any]:
    payload = _canonical_pack_payload(doc)
    out = dict(payload)
    out["pack_digest"] = canonical_digest(payload)
    return out


def digest_governance_evidence_pack_document(doc: GovernanceEvidencePackDocument) -> str:
    return canonical_digest(_canonical_pack_payload(doc))


def validate_governance_evidence_pack_document(data: Any) -> ValidationResult:
    doc, parse_issues = governance_evidence_pack_document_from_dict(data)
    issues = list(parse_issues)
    if doc is None:
        return ValidationResult(ok=False, issues=tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message))))

    computed_pack = digest_governance_evidence_pack_document(doc)
    if doc.pack_digest is not None and doc.pack_digest != computed_pack:
        issues.append(
            ValidationIssue(
                code="pack_digest_mismatch",
                message="pack_digest does not match canonical digest of pack fields",
                path="pack_digest",
            )
        )

    expected_manifest = EvidencePackDigestManifest(
        entries=tuple(
            EvidencePackDigestManifestEntry(artifact_id=a.artifact_id, content_digest=a.content_digest)
            for a in sorted(doc.artifacts, key=lambda x: x.artifact_id)
        )
    )
    if canonical_digest_manifest(doc.digest_manifest) != canonical_digest_manifest(expected_manifest):
        issues.append(
            ValidationIssue(
                code="digest_manifest_mismatch",
                message="digest_manifest must match canonical entries derived from artifacts (sorted by artifact_id)",
                path="digest_manifest",
            )
        )

    for i, a in enumerate(doc.artifacts):
        base = f"artifacts[{i}]"
        if a.evidence_type == EvidencePackEvidenceType.GOVERNED and len(a.control_refs) == 0:
            issues.append(
                ValidationIssue(
                    code="control_refs_required",
                    message="GOVERNED artifacts require non-empty control_refs",
                    path=f"{base}.control_refs",
                )
            )

    issues_sorted = tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))
    ok = len(issues_sorted) == 0
    d = computed_pack if ok else None
    return ValidationResult(ok=ok, issues=issues_sorted, digest=d)
