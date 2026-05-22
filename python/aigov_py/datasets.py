from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class DatasetStatus(Enum):
    REGISTERED = "REGISTERED"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"


class DatasetClassification(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


_DATASET_STATUS_VALUES = frozenset(s.value for s in DatasetStatus)
_DATASET_CLASSIFICATION_VALUES = frozenset(c.value for c in DatasetClassification)

_HEX64 = set("0123456789abcdef")

_ERR_APPROVER_ID_REQUIRED = "approver_id is required and must be non-empty"
_ERR_APPROVER_CANNOT_SELF_APPROVE = "owner cannot approve own dataset"
_ERR_CLASSIFICATION_INVALID = "classification must be one of: CONFIDENTIAL, INTERNAL, PUBLIC, RESTRICTED"
_ERR_DATASET_DIGEST_INVALID = (
    "dataset_digest must be 64 hex characters or sha256: followed by 64 hex characters"
)
_ERR_DATASET_DIGEST_REQUIRED = "dataset_digest is required"
_ERR_DATASET_ID_REQUIRED = "dataset_id is required and must be non-empty"
_ERR_LINEAGE_DATASET_ID_REQUIRED = "lineage dataset_id is required and must be non-empty"
_ERR_LINEAGE_DIGEST_MISMATCH = "lineage dataset_digest does not match dataset record"
_ERR_LINEAGE_DIGEST_REQUIRED = "lineage dataset_digest is required and valid"
_ERR_LINEAGE_ID_MISMATCH = "lineage dataset_id does not match dataset record"
_ERR_MANIFEST_REF_REQUIRED = "manifest_ref is required and must be non-empty"
_ERR_OWNER_ID_REQUIRED_FOR_APPROVAL = "owner_id is required and must be non-empty for approval validation"
_ERR_OWNER_REQUIRED = "owner is required and must be non-empty"
_ERR_STATUS_UNKNOWN = "status is not a known dataset status"
_ERR_TENANT_ID_REQUIRED = "tenant_id is required and must be non-empty"
_ERR_EXPIRATION_UTC_REQUIRED = "approval expiration must be timezone-aware UTC when present"


def _is_hex64(value: str) -> bool:
    if len(value) != 64:
        return False
    return all(ch in _HEX64 for ch in value.lower())


def _digest_format_valid(digest: str) -> bool:
    s = (digest or "").strip()
    if not s:
        return False
    low = s.lower()
    if low.startswith("sha256:"):
        rest = low[7:].strip()
        return _is_hex64(rest)
    return _is_hex64(low)


def _canonical_digest(digest: str) -> str | None:
    if not _digest_format_valid(digest):
        return None
    low = (digest or "").strip().lower()
    if low.startswith("sha256:"):
        return low[7:].strip()
    return low


@dataclass(frozen=True)
class DatasetRecord:
    """Governance metadata for a registered dataset (primitive; not enforced at runtime)."""

    dataset_id: str
    tenant_id: str
    dataset_digest: str
    manifest_ref: str
    owner: str
    classification: str
    status: str


@dataclass(frozen=True)
class DatasetApproval:
    """Approval metadata; separation of duties validated against dataset owner."""

    approver_id: str
    expires_at: datetime | None = None


@dataclass(frozen=True)
class DatasetLineageRef:
    """Lineage reference: binds a dataset identity to an integrity digest."""

    dataset_id: str
    dataset_digest: str


def _expiration_is_aware_utc(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        return False
    off = expires_at.utcoffset()
    if off is None:
        return False
    return off == timedelta(0)


def validate_dataset_record(record: DatasetRecord) -> tuple[str, ...]:
    """Return sorted, deterministic error messages; empty tuple means valid."""
    errors: list[str] = []

    if not (record.dataset_id or "").strip():
        errors.append(_ERR_DATASET_ID_REQUIRED)
    if not (record.tenant_id or "").strip():
        errors.append(_ERR_TENANT_ID_REQUIRED)

    dig = (record.dataset_digest or "").strip()
    if not dig:
        errors.append(_ERR_DATASET_DIGEST_REQUIRED)
    elif not _digest_format_valid(record.dataset_digest):
        errors.append(_ERR_DATASET_DIGEST_INVALID)

    if not (record.manifest_ref or "").strip():
        errors.append(_ERR_MANIFEST_REF_REQUIRED)
    if not (record.owner or "").strip():
        errors.append(_ERR_OWNER_REQUIRED)

    cls_raw = (record.classification or "").strip()
    if cls_raw not in _DATASET_CLASSIFICATION_VALUES:
        errors.append(_ERR_CLASSIFICATION_INVALID)

    st_raw = (record.status or "").strip()
    if st_raw not in _DATASET_STATUS_VALUES:
        errors.append(_ERR_STATUS_UNKNOWN)

    return tuple(sorted(errors))


def validate_dataset_approval(approval: DatasetApproval, *, owner_id: str) -> tuple[str, ...]:
    """Return sorted, deterministic error messages; empty tuple means valid."""
    errors: list[str] = []

    if not (owner_id or "").strip():
        errors.append(_ERR_OWNER_ID_REQUIRED_FOR_APPROVAL)

    if not (approval.approver_id or "").strip():
        errors.append(_ERR_APPROVER_ID_REQUIRED)

    if (
        (owner_id or "").strip()
        and (approval.approver_id or "").strip()
        and owner_id.strip() == approval.approver_id.strip()
    ):
        errors.append(_ERR_APPROVER_CANNOT_SELF_APPROVE)

    if approval.expires_at is not None:
        if not _expiration_is_aware_utc(approval.expires_at):
            errors.append(_ERR_EXPIRATION_UTC_REQUIRED)

    return tuple(sorted(errors))


def validate_dataset_lineage(
    lineage: DatasetLineageRef,
    record: DatasetRecord | None = None,
) -> tuple[str, ...]:
    """Return sorted, deterministic error messages; empty tuple means valid."""
    errors: list[str] = []

    if not (lineage.dataset_id or "").strip():
        errors.append(_ERR_LINEAGE_DATASET_ID_REQUIRED)

    if not (lineage.dataset_digest or "").strip():
        errors.append(_ERR_LINEAGE_DIGEST_REQUIRED)
    elif not _digest_format_valid(lineage.dataset_digest):
        errors.append(_ERR_LINEAGE_DIGEST_REQUIRED)

    if record is not None:
        rec_errs = validate_dataset_record(record)
        if rec_errs:
            errors.extend(rec_errs)
        elif (lineage.dataset_id or "").strip() != (record.dataset_id or "").strip():
            errors.append(_ERR_LINEAGE_ID_MISMATCH)
        elif _digest_format_valid(lineage.dataset_digest) and _digest_format_valid(
            record.dataset_digest
        ):
            lc = _canonical_digest(lineage.dataset_digest)
            rc = _canonical_digest(record.dataset_digest)
            if lc != rc:
                errors.append(_ERR_LINEAGE_DIGEST_MISMATCH)

    return tuple(sorted(errors))
