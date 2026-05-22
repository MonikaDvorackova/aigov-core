from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuntimeControlStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RuntimeRiskClass(Enum):
    MINIMAL = "MINIMAL"
    LIMITED = "LIMITED"
    HIGH = "HIGH"
    PROHIBITED = "PROHIBITED"


class RuntimeGovernanceVerdict(Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class RuntimeControlEvaluation:
    """Per-control outcome for a runtime decision; refs and codes are opaque — no raw user content."""

    control_id: str
    status: RuntimeControlStatus
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class DatasetLineageRef:
    dataset_id: str
    dataset_digest: str


@dataclass(frozen=True)
class HumanOverrideRef:
    override_id: str
    target_decision_id: str


@dataclass(frozen=True)
class RuntimeGovernanceContext:
    """Integration-shaped planning context linking a runtime decision to controls, lineage, overrides, and AI Act refs."""

    runtime_decision_id: str
    correlation_id: str
    tenant_id: str
    artifact_digest: str
    policy_bundle_version: str
    risk_class: RuntimeRiskClass
    control_evaluations: tuple[RuntimeControlEvaluation, ...]
    dataset_lineage_refs: tuple[DatasetLineageRef, ...] = ()
    human_override_ref: HumanOverrideRef | None = None
    ai_act_requirement_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeGovernanceSummary:
    verdict: RuntimeGovernanceVerdict
    validation_errors: tuple[str, ...]
    failing_control_ids: tuple[str, ...]


_ERR_RUNTIME_DECISION_ID = "runtime_decision_id is required and must be non-empty"
_ERR_CORRELATION_ID = "correlation_id is required and must be non-empty"
_ERR_TENANT_ID = "tenant_id is required and must be non-empty"
_ERR_ARTIFACT_DIGEST = (
    "artifact_digest is required and must be 64 hex or sha256:<64 hex>"
)
_ERR_POLICY_BUNDLE_VERSION = (
    "policy_bundle_version is required and must be non-empty"
)
_ERR_RISK_CLASS = (
    "risk_class is required and must be a member of RuntimeRiskClass"
)
_ERR_CONTROL_ID = (
    "each control evaluation must have a non-empty control_id after stripping"
)
_ERR_CONTROL_STATUS = (
    "each control evaluation status must be a member of RuntimeControlStatus"
)
_ERR_FAIL_REASONS = (
    "status FAIL requires at least one non-empty reason code after stripping"
)
_ERR_LINEAGE_DATASET_ID = (
    "dataset_lineage_refs: dataset_id is required and must be non-empty"
)
_ERR_LINEAGE_DIGEST = (
    "dataset_lineage_refs: dataset_digest must be valid 64 hex or sha256:<64 hex>"
)
_ERR_OVERRIDE_ID = (
    "human_override_ref: override_id is required and must be non-empty"
)
_ERR_OVERRIDE_TARGET = (
    "human_override_ref: target_decision_id must match runtime_decision_id"
)
_ERR_AI_ACT_REF = (
    "ai_act_requirement_refs: each entry must be a non-empty string after stripping"
)


def _strip_norm(s: str) -> str:
    return (s or "").strip()


def is_valid_digest_token(value: str) -> bool:
    """True for exactly 64 hex digits or sha256:<64 hex> (case-insensitive hex)."""
    t = _strip_norm(value)
    if not t:
        return False
    head = "sha256:"
    if t.lower().startswith(head):
        rest = t[len(head) :].strip().lower()
        body = rest
    elif len(t) == 64:
        body = t.lower()
    else:
        return False
    if len(body) != 64:
        return False
    for c in body:
        if c not in "0123456789abcdef":
            return False
    return True


def validate_runtime_governance_context(
    ctx: RuntimeGovernanceContext,
) -> tuple[str, ...]:
    """Return sorted, deterministic error messages; empty tuple means valid."""
    errors: list[str] = []

    if not _strip_norm(ctx.runtime_decision_id):
        errors.append(_ERR_RUNTIME_DECISION_ID)
    if not _strip_norm(ctx.correlation_id):
        errors.append(_ERR_CORRELATION_ID)
    if not _strip_norm(ctx.tenant_id):
        errors.append(_ERR_TENANT_ID)
    if not is_valid_digest_token(ctx.artifact_digest):
        errors.append(_ERR_ARTIFACT_DIGEST)
    if not _strip_norm(ctx.policy_bundle_version):
        errors.append(_ERR_POLICY_BUNDLE_VERSION)
    if not isinstance(ctx.risk_class, RuntimeRiskClass):
        errors.append(_ERR_RISK_CLASS)

    for ev in ctx.control_evaluations:
        if not isinstance(ev.status, RuntimeControlStatus):
            errors.append(_ERR_CONTROL_STATUS)
        if not _strip_norm(ev.control_id):
            errors.append(_ERR_CONTROL_ID)
        if isinstance(ev.status, RuntimeControlStatus) and (
            ev.status == RuntimeControlStatus.FAIL
        ):
            rc = tuple(_strip_norm(x) for x in ev.reason_codes if _strip_norm(x))
            if len(rc) == 0:
                errors.append(_ERR_FAIL_REASONS)

    for ref in ctx.dataset_lineage_refs:
        if not _strip_norm(ref.dataset_id):
            errors.append(_ERR_LINEAGE_DATASET_ID)
        if not is_valid_digest_token(ref.dataset_digest):
            errors.append(_ERR_LINEAGE_DIGEST)

    ov = ctx.human_override_ref
    if ov is not None:
        if not _strip_norm(ov.override_id):
            errors.append(_ERR_OVERRIDE_ID)
        elif _strip_norm(ov.target_decision_id) != _strip_norm(
            ctx.runtime_decision_id
        ):
            errors.append(_ERR_OVERRIDE_TARGET)

    for rid in ctx.ai_act_requirement_refs:
        if not _strip_norm(rid):
            errors.append(_ERR_AI_ACT_REF)
            break

    return tuple(sorted(frozenset(errors)))


def _failing_control_ids(ctx: RuntimeGovernanceContext) -> tuple[str, ...]:
    pairs: list[tuple[str, int]] = []
    for i, ev in enumerate(ctx.control_evaluations):
        if ev.status == RuntimeControlStatus.FAIL:
            pairs.append((_strip_norm(ev.control_id) or ev.control_id, i))
    pairs.sort(key=lambda p: (p[0], p[1]))
    return tuple(cid for cid, _ in pairs)


def summarize_runtime_governance(
    ctx: RuntimeGovernanceContext,
) -> RuntimeGovernanceSummary:
    """Deterministic verdict from control outcomes and validated context fields (planning only)."""
    validation_errors = validate_runtime_governance_context(ctx)
    failing = _failing_control_ids(ctx)
    if failing:
        return RuntimeGovernanceSummary(
            verdict=RuntimeGovernanceVerdict.INVALID,
            validation_errors=validation_errors,
            failing_control_ids=failing,
        )
    if validation_errors:
        return RuntimeGovernanceSummary(
            verdict=RuntimeGovernanceVerdict.BLOCKED,
            validation_errors=validation_errors,
            failing_control_ids=(),
        )
    return RuntimeGovernanceSummary(
        verdict=RuntimeGovernanceVerdict.VALID,
        validation_errors=(),
        failing_control_ids=(),
    )
