from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from aigov_py.experiments.gate_model import Verdict, decision_gate_verdict_from_fields
from aigov_py.experiments.scenario_fields import make_base_fields
from aigov_py.standards.common import (
    ValidationIssue,
    ValidationResult,
    canonical_digest,
    find_raw_content_fields,
)

_EXPECTED_SCHEMA = "govai.standards.governance_decision_trace.v1"

# Closed set of gate input keys (same bundle as experiments scenario_fields.make_base_fields).
_GATE_FIELD_KEYS: frozenset[str] = frozenset(make_base_fields().keys())


@dataclass(frozen=True)
class GovernanceDecisionTraceDocument:
    schema_version: str
    trace_id: str
    tenant_scope: str
    run_id: str
    recorded_gate_verdict: Verdict
    gate_inputs: dict[str, Any]


def governance_decision_trace_from_dict(
    data: Any,
) -> tuple[GovernanceDecisionTraceDocument | None, tuple[ValidationIssue, ...]]:
    issues: list[ValidationIssue] = []
    if not isinstance(data, Mapping):
        return None, (ValidationIssue(code="root_invalid", message="document root must be an object", path=""),)

    issues.extend(find_raw_content_fields(data))

    sv = data.get("schema_version")
    if not isinstance(sv, str) or not sv.strip():
        issues.append(
            ValidationIssue(code="schema_version_required", message="schema_version is required", path="schema_version")
        )

    tid = data.get("trace_id")
    if not isinstance(tid, str) or not tid.strip():
        issues.append(ValidationIssue(code="trace_id_required", message="trace_id is required", path="trace_id"))

    ts = data.get("tenant_scope")
    if not isinstance(ts, str) or not ts.strip():
        issues.append(
            ValidationIssue(code="tenant_scope_required", message="tenant_scope is required", path="tenant_scope")
        )

    rid = data.get("run_id")
    if not isinstance(rid, str) or not rid.strip():
        issues.append(ValidationIssue(code="run_id_required", message="run_id is required", path="run_id"))

    rv = data.get("recorded_gate_verdict")
    verdict: Verdict | None = None
    if rv not in ("VALID", "INVALID", "BLOCKED"):
        issues.append(
            ValidationIssue(
                code="recorded_gate_verdict_invalid",
                message="recorded_gate_verdict must be VALID, INVALID, or BLOCKED",
                path="recorded_gate_verdict",
            )
        )
    else:
        verdict = rv  # type: ignore[assignment]

    gi_raw = data.get("gate_inputs")
    gate_inputs: dict[str, Any] | None = None
    if not isinstance(gi_raw, Mapping):
        issues.append(
            ValidationIssue(code="gate_inputs_required", message="gate_inputs must be an object", path="gate_inputs")
        )
    else:
        gi_dict = dict(gi_raw)
        extra = set(gi_dict.keys()) - _GATE_FIELD_KEYS
        missing = _GATE_FIELD_KEYS - set(gi_dict.keys())
        if extra:
            issues.append(
                ValidationIssue(
                    code="gate_inputs_unknown_keys",
                    message=f"gate_inputs contains unknown keys: {sorted(extra)!r}",
                    path="gate_inputs",
                )
            )
        if missing:
            issues.append(
                ValidationIssue(
                    code="gate_inputs_missing_keys",
                    message=f"gate_inputs missing required keys: {sorted(missing)!r}",
                    path="gate_inputs",
                )
            )
        if not extra and not missing:
            gate_inputs = gi_dict

    if (
        not isinstance(sv, str)
        or not sv.strip()
        or not isinstance(tid, str)
        or not tid.strip()
        or not isinstance(ts, str)
        or not ts.strip()
        or not isinstance(rid, str)
        or not rid.strip()
        or verdict is None
        or gate_inputs is None
    ):
        return None, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))

    doc = GovernanceDecisionTraceDocument(
        schema_version=sv.strip(),
        trace_id=tid.strip(),
        tenant_scope=ts.strip(),
        run_id=rid.strip(),
        recorded_gate_verdict=verdict,
        gate_inputs=gate_inputs,
    )
    return doc, tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))


def _canonical_trace_payload(doc: GovernanceDecisionTraceDocument) -> dict[str, Any]:
    # Deterministic key order for gate_inputs matches make_base_fields declaration order.
    ordered_keys = sorted(doc.gate_inputs.keys())
    gi = {k: doc.gate_inputs[k] for k in ordered_keys}
    return {
        "gate_inputs": gi,
        "recorded_gate_verdict": doc.recorded_gate_verdict,
        "run_id": doc.run_id,
        "schema_version": doc.schema_version,
        "tenant_scope": doc.tenant_scope,
        "trace_id": doc.trace_id,
    }


def canonical_governance_decision_trace_document(doc: GovernanceDecisionTraceDocument) -> dict[str, Any]:
    return _canonical_trace_payload(doc)


def digest_governance_decision_trace_document(doc: GovernanceDecisionTraceDocument) -> str:
    return canonical_digest(_canonical_trace_payload(doc))


def validate_governance_decision_trace_document(data: Any) -> ValidationResult:
    doc, parse_issues = governance_decision_trace_from_dict(data)
    issues = list(parse_issues)
    if doc is None:
        return ValidationResult(ok=False, issues=tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message))))

    if doc.schema_version != _EXPECTED_SCHEMA:
        issues.append(
            ValidationIssue(
                code="schema_version_unsupported",
                message=f"schema_version must be exactly {_EXPECTED_SCHEMA!r} for this interchange revision",
                path="schema_version",
            )
        )
    else:
        try:
            computed: Verdict = decision_gate_verdict_from_fields(doc.gate_inputs)
        except (KeyError, TypeError, ValueError) as e:
            issues.append(
                ValidationIssue(
                    code="gate_inputs_not_evaluable",
                    message=f"gate_inputs cannot be evaluated by the authoritative gate model: {e}",
                    path="gate_inputs",
                )
            )
            computed = "INVALID"  # unused
        else:
            if doc.recorded_gate_verdict != computed:
                issues.append(
                    ValidationIssue(
                        code="recorded_verdict_mismatch",
                        message=(
                            f"recorded_gate_verdict {doc.recorded_gate_verdict!r} does not match "
                            f"authoritative recomputation {computed!r}"
                        ),
                        path="recorded_gate_verdict",
                    )
                )

    issues_sorted = tuple(sorted(issues, key=lambda i: (i.path, i.code, i.message)))
    ok = len(issues_sorted) == 0
    d = digest_governance_decision_trace_document(doc) if ok else None
    return ValidationResult(ok=ok, issues=issues_sorted, digest=d)
