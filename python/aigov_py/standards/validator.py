from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from aigov_py.standards import registry
from aigov_py.standards.common import ValidationIssue, ValidationResult


def _issue_dict(i: ValidationIssue) -> dict[str, str]:
    return {"code": i.code, "message": i.message, "path": i.path}


def _infer_schema_version(data: Any) -> str | None:
    if not isinstance(data, Mapping):
        return None
    sv = data.get("schema_version")
    if isinstance(sv, str) and sv.strip():
        return sv.strip()
    return None


def _infer_artifact_type_from_version(sv: str) -> str | None:
    row = registry.resolve_registered(sv)
    return row.artifact_type if row else None


@dataclass
class ConformanceReport:
    """Structured conformance result for machine and human consumers."""

    ok: bool
    artifact_type: str
    version: str
    checks: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, str]] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)
    digest: str | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "artifact_type": self.artifact_type,
            "checks": list(self.checks),
            "digest": self.digest,
            "failures": list(self.failures),
            "ok": self.ok,
            "version": self.version,
            "warnings": list(self.warnings),
        }
        return dict(sorted(out.items()))


def validate_conformance(
    data: Any,
    *,
    artifact_type: str | None = None,
) -> ConformanceReport:
    """
    Deterministic conformance validation for registered governance interchange documents.

    When ``artifact_type`` is omitted, it is inferred from ``schema_version`` using the explicit registry.
    """
    checks: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []

    if not isinstance(data, Mapping):
        return ConformanceReport(
            ok=False,
            artifact_type=artifact_type or "",
            version="",
            checks=[{"detail": "root must be a JSON object", "id": "root_kind", "ok": False}],
            failures=[{"code": "root_invalid", "message": "document root must be an object", "path": ""}],
            warnings=warnings,
        )

    sv = _infer_schema_version(data)
    if not sv:
        return ConformanceReport(
            ok=False,
            artifact_type=artifact_type or "",
            version="",
            checks=[{"id": "schema_version_present", "ok": False}],
            failures=[
                {
                    "code": "schema_version_required",
                    "message": "schema_version is required for interchange conformance",
                    "path": "schema_version",
                }
            ],
            warnings=warnings,
        )

    inferred_type = _infer_artifact_type_from_version(sv)
    if artifact_type is not None and artifact_type.strip() and inferred_type != artifact_type.strip():
        return ConformanceReport(
            ok=False,
            artifact_type=inferred_type or "",
            version=sv,
            checks=[{"expected": artifact_type, "id": "artifact_type_match", "inferred": inferred_type, "ok": False}],
            failures=[
                {
                    "code": "artifact_type_mismatch",
                    "message": f"document infers {inferred_type!r} but {artifact_type!r} was requested",
                    "path": "schema_version",
                }
            ],
            warnings=warnings,
        )

    if inferred_type is None:
        return ConformanceReport(
            ok=False,
            artifact_type="",
            version=sv,
            checks=[{"id": "registry_lookup", "ok": False}],
            failures=[
                {
                    "code": "unknown_schema_version",
                    "message": "schema_version is not listed in the governance standards registry",
                    "path": "schema_version",
                }
            ],
            warnings=warnings,
        )

    fn: Callable[[Any], ValidationResult] | None = registry.validator_for_schema_version(sv)
    if fn is None:
        return ConformanceReport(
            ok=False,
            artifact_type=inferred_type,
            version=sv,
            checks=[{"id": "validator_binding", "ok": False}],
            failures=[{"code": "internal_error", "message": "no validator bound for registered schema_version", "path": ""}],
            warnings=warnings,
        )

    checks.append({"id": "registry_lookup", "ok": True})
    res = fn(data)
    checks.append({"id": "deterministic_rules", "issue_count": len(res.issues), "ok": res.ok})

    failures = [_issue_dict(i) for i in res.sorted_issues()]

    return ConformanceReport(
        ok=bool(res.ok),
        artifact_type=inferred_type,
        version=sv,
        checks=checks,
        failures=failures,
        warnings=warnings,
        digest=res.digest,
    )
