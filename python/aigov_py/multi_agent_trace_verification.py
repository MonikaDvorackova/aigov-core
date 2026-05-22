from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Optional

from aigov_py.canonical_json import canonical_dumps


class TraceVerificationStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class TraceVerificationFinding:
    code: str
    status: TraceVerificationStatus
    message: str
    subject: Optional[str] = None

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "status": self.status.value,
            "message": self.message,
            "subject": self.subject,
        }


@dataclass(frozen=True)
class TraceVerificationRequirement:
    signatures_required: bool = False
    strict_signatures: bool = False
    event_chain_required: bool = False
    event_count_expected: int = 0

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "signatures_required": bool(self.signatures_required),
            "strict_signatures": bool(self.strict_signatures),
            "event_chain_required": bool(self.event_chain_required),
            "event_count_expected": int(self.event_count_expected),
        }


@dataclass(frozen=True)
class TraceSignatureExpectation:
    action_id: str
    signing_key_ref: Optional[str] = None
    signature_algorithm: Optional[str] = None
    expected_signature_ref: Optional[str] = None

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "signing_key_ref": self.signing_key_ref,
            "signature_algorithm": self.signature_algorithm,
            "expected_signature_ref": self.expected_signature_ref,
        }


@dataclass(frozen=True)
class TracePolicySnapshotExpectation:
    policy_snapshot_id: str

    def to_canonical_dict(self) -> dict[str, Any]:
        return {"policy_snapshot_id": self.policy_snapshot_id}


@dataclass(frozen=True)
class TraceVerificationPlan:
    tenant_id: str
    trace_id: str
    trace_digest: str
    policy_snapshot_id: str
    event_count_expected: int
    requirements: TraceVerificationRequirement
    signature_expectations: list[TraceSignatureExpectation] = field(default_factory=list)
    policy_snapshot_expectation: Optional[TracePolicySnapshotExpectation] = None
    event_digest_chain_refs: Optional[list[str]] = None
    findings: list[TraceVerificationFinding] = field(default_factory=list)
    status: TraceVerificationStatus = TraceVerificationStatus.NOT_APPLICABLE
    plan_digest: str = ""
    schema: str = "aigov.trace_verification_plan.v1"

    def to_canonical_dict_excluding_digest(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "tenant_id": self.tenant_id,
            "trace_id": self.trace_id,
            "trace_digest": self.trace_digest,
            "policy_snapshot_id": self.policy_snapshot_id,
            "event_count_expected": int(self.event_count_expected),
            "requirements": self.requirements.to_canonical_dict(),
            "signature_expectations": [s.to_canonical_dict() for s in self.signature_expectations],
            "policy_snapshot_expectation": (
                None if self.policy_snapshot_expectation is None else self.policy_snapshot_expectation.to_canonical_dict()
            ),
            "event_digest_chain_refs": self.event_digest_chain_refs,
            "status": self.status.value,
            "findings": [f.to_canonical_dict() for f in self.findings],
        }


_HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_SHA256_PREFIXED_RE = re.compile(r"^sha256:([0-9a-fA-F]{64})$")


def _is_valid_trace_digest(s: str) -> bool:
    if _HEX64_RE.match(s):
        return True
    return _SHA256_PREFIXED_RE.match(s) is not None


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _sorted_findings(findings: Iterable[TraceVerificationFinding]) -> list[TraceVerificationFinding]:
    return sorted(findings, key=lambda f: (f.code, f.subject or "", f.status.value, f.message))


def _summarize_status(findings: list[TraceVerificationFinding]) -> TraceVerificationStatus:
    if not findings:
        return TraceVerificationStatus.NOT_APPLICABLE

    statuses = [f.status for f in findings]
    if any(s == TraceVerificationStatus.FAIL for s in statuses):
        return TraceVerificationStatus.FAIL
    if any(s == TraceVerificationStatus.WARN for s in statuses):
        return TraceVerificationStatus.WARN

    applicable = [s for s in statuses if s != TraceVerificationStatus.NOT_APPLICABLE]
    if not applicable:
        return TraceVerificationStatus.NOT_APPLICABLE
    return TraceVerificationStatus.PASS


def plan_trace_verification(
    *,
    tenant_id: str,
    trace_id: str,
    trace_digest: str,
    policy_snapshot_id: str,
    event_count_expected: int,
    requirements: TraceVerificationRequirement,
    signature_expectations: Optional[list[TraceSignatureExpectation]] = None,
    event_digest_chain_refs: Optional[list[str]] = None,
) -> TraceVerificationPlan:
    """
    Planning-only multi-agent trace verification.

    This function does NOT verify signatures or keys. It produces a deterministic plan:
    - normalized findings (stable codes)
    - summary status (PASS/WARN/FAIL/NOT_APPLICABLE)
    - plan_digest = sha256(canonical_json(plan_without_plan_digest))
    """
    findings: list[TraceVerificationFinding] = []

    tenant_id = (tenant_id or "").strip()
    trace_id = (trace_id or "").strip()
    trace_digest = (trace_digest or "").strip()
    policy_snapshot_id = (policy_snapshot_id or "").strip()

    if not tenant_id:
        findings.append(
            TraceVerificationFinding(
                code="TENANT_ID_REQUIRED",
                status=TraceVerificationStatus.FAIL,
                message="tenant_id is required",
            )
        )

    if not trace_id:
        findings.append(
            TraceVerificationFinding(
                code="TRACE_ID_REQUIRED",
                status=TraceVerificationStatus.FAIL,
                message="trace_id is required",
            )
        )

    if not trace_digest:
        findings.append(
            TraceVerificationFinding(
                code="TRACE_DIGEST_REQUIRED",
                status=TraceVerificationStatus.FAIL,
                message="trace_digest is required",
            )
        )
    elif not _is_valid_trace_digest(trace_digest):
        findings.append(
            TraceVerificationFinding(
                code="TRACE_DIGEST_INVALID",
                status=TraceVerificationStatus.FAIL,
                message="trace_digest must be 64 hex or sha256:<64 hex>",
                subject=trace_digest,
            )
        )

    if not policy_snapshot_id:
        findings.append(
            TraceVerificationFinding(
                code="POLICY_SNAPSHOT_ID_REQUIRED",
                status=TraceVerificationStatus.FAIL,
                message="policy_snapshot_id is required",
            )
        )

    if event_count_expected < 0:
        findings.append(
            TraceVerificationFinding(
                code="EVENT_COUNT_EXPECTED_INVALID",
                status=TraceVerificationStatus.FAIL,
                message="event_count_expected must be >= 0",
                subject=str(event_count_expected),
            )
        )
    else:
        findings.append(
            TraceVerificationFinding(
                code="EVENT_COUNT_EXPECTED_OK",
                status=TraceVerificationStatus.PASS,
                message="event_count_expected is valid",
                subject=str(event_count_expected),
            )
        )

    sig_exps = list(signature_expectations or [])
    sig_exps = sorted(sig_exps, key=lambda s: (s.action_id, s.signing_key_ref or "", s.signature_algorithm or "", s.expected_signature_ref or ""))

    if requirements.signatures_required:
        if not sig_exps:
            findings.append(
                TraceVerificationFinding(
                    code="SIGNATURES_REQUIRED_NO_ACTIONS",
                    status=TraceVerificationStatus.WARN,
                    message="signatures_required=True but no signature expectations were provided",
                )
            )
        for s in sig_exps:
            subj = s.action_id
            if not (s.signing_key_ref or "").strip():
                findings.append(
                    TraceVerificationFinding(
                        code="SIGNING_KEY_REF_REQUIRED",
                        status=TraceVerificationStatus.FAIL,
                        message="signing_key_ref is required when signatures_required=True",
                        subject=subj,
                    )
                )
            else:
                findings.append(
                    TraceVerificationFinding(
                        code="SIGNING_KEY_REF_PRESENT",
                        status=TraceVerificationStatus.PASS,
                        message="signing_key_ref present",
                        subject=subj,
                    )
                )

            if not (s.signature_algorithm or "").strip():
                findings.append(
                    TraceVerificationFinding(
                        code="SIGNATURE_ALGORITHM_REQUIRED",
                        status=TraceVerificationStatus.FAIL,
                        message="signature_algorithm is required when signatures_required=True",
                        subject=subj,
                    )
                )
            else:
                findings.append(
                    TraceVerificationFinding(
                        code="SIGNATURE_ALGORITHM_PRESENT",
                        status=TraceVerificationStatus.PASS,
                        message="signature_algorithm present",
                        subject=subj,
                    )
                )

            if not (s.expected_signature_ref or "").strip():
                findings.append(
                    TraceVerificationFinding(
                        code="EXPECTED_SIGNATURE_REF_MISSING",
                        status=(
                            TraceVerificationStatus.FAIL
                            if requirements.strict_signatures
                            else TraceVerificationStatus.WARN
                        ),
                        message=(
                            "expected_signature_ref is required when strict_signatures=True"
                            if requirements.strict_signatures
                            else "expected_signature_ref is recommended for planning"
                        ),
                        subject=subj,
                    )
                )
            else:
                findings.append(
                    TraceVerificationFinding(
                        code="EXPECTED_SIGNATURE_REF_PRESENT",
                        status=TraceVerificationStatus.PASS,
                        message="expected_signature_ref present",
                        subject=subj,
                    )
                )
    else:
        findings.append(
            TraceVerificationFinding(
                code="SIGNATURES_NOT_REQUIRED",
                status=TraceVerificationStatus.NOT_APPLICABLE,
                message="signatures_required=False",
            )
        )

    chain_refs = event_digest_chain_refs
    if requirements.event_chain_required:
        if not chain_refs:
            findings.append(
                TraceVerificationFinding(
                    code="EVENT_CHAIN_REQUIRED_MISSING",
                    status=TraceVerificationStatus.FAIL,
                    message="event_chain_required=True but event_digest_chain_refs is missing or empty",
                )
            )
        else:
            nonempty = [c for c in chain_refs if isinstance(c, str) and c.strip()]
            if not nonempty:
                findings.append(
                    TraceVerificationFinding(
                        code="EVENT_CHAIN_REQUIRED_EMPTY",
                        status=TraceVerificationStatus.FAIL,
                        message="event_chain_required=True but event_digest_chain_refs contains no non-empty refs",
                    )
                )
            else:
                findings.append(
                    TraceVerificationFinding(
                        code="EVENT_CHAIN_PRESENT",
                        status=TraceVerificationStatus.PASS,
                        message="event_digest_chain_refs present",
                        subject=str(len(nonempty)),
                    )
                )
                chain_refs = nonempty
    else:
        if not chain_refs:
            findings.append(
                TraceVerificationFinding(
                    code="EVENT_CHAIN_NOT_REQUIRED",
                    status=TraceVerificationStatus.NOT_APPLICABLE,
                    message="event_chain_required=False and no chain refs provided",
                )
            )
            chain_refs = None
        else:
            nonempty = [c for c in chain_refs if isinstance(c, str) and c.strip()]
            findings.append(
                TraceVerificationFinding(
                    code="EVENT_CHAIN_OPTIONAL_PRESENT",
                    status=TraceVerificationStatus.PASS,
                    message="event_chain_required=False and chain refs provided",
                    subject=str(len(nonempty)),
                )
            )
            chain_refs = nonempty

    sorted_findings = _sorted_findings(findings)
    status = _summarize_status(sorted_findings)

    plan = TraceVerificationPlan(
        tenant_id=tenant_id,
        trace_id=trace_id,
        trace_digest=trace_digest,
        policy_snapshot_id=policy_snapshot_id,
        event_count_expected=event_count_expected,
        requirements=requirements,
        signature_expectations=sig_exps,
        policy_snapshot_expectation=(
            None if not policy_snapshot_id else TracePolicySnapshotExpectation(policy_snapshot_id=policy_snapshot_id)
        ),
        event_digest_chain_refs=chain_refs,
        findings=sorted_findings,
        status=status,
        plan_digest="",
    )

    plan_body = canonical_dumps(plan.to_canonical_dict_excluding_digest())
    object.__setattr__(plan, "plan_digest", _sha256_hex(plan_body))
    return plan

