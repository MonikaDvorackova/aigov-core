from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aigov_py.datasets import (
    DatasetApproval,
    DatasetLineageRef,
    DatasetRecord,
    validate_dataset_approval,
    validate_dataset_lineage,
    validate_dataset_record,
)

_HEX64 = "a" * 64


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc)


def _base_record(**kwargs: str) -> DatasetRecord:
    defaults = {
        "dataset_id": "ds-1",
        "tenant_id": "tenant-1",
        "dataset_digest": _HEX64,
        "manifest_ref": "s3://bucket/manifest.json",
        "owner": "alice",
        "classification": "INTERNAL",
        "status": "REGISTERED",
    }
    defaults.update(kwargs)
    return DatasetRecord(**defaults)


def test_valid_dataset_record_passes() -> None:
    rec = _base_record()
    assert validate_dataset_record(rec) == ()


def test_missing_dataset_id_fails() -> None:
    rec = _base_record(dataset_id="  ")
    errs = validate_dataset_record(rec)
    assert errs
    assert "dataset_id is required and must be non-empty" in errs


def test_invalid_digest_fails() -> None:
    rec = _base_record(dataset_digest="not-a-digest")
    errs = validate_dataset_record(rec)
    assert errs
    assert (
        "dataset_digest must be 64 hex characters or sha256: followed by 64 hex characters"
        in errs
    )


def test_sha256_prefix_digest_passes() -> None:
    rec = _base_record(dataset_digest=f"sha256:{_HEX64}")
    assert validate_dataset_record(rec) == ()


def test_invalid_classification_fails() -> None:
    rec = _base_record(classification="TOP_SECRET")
    errs = validate_dataset_record(rec)
    assert errs
    assert (
        "classification must be one of: CONFIDENTIAL, INTERNAL, PUBLIC, RESTRICTED" in errs
    )


def test_approval_requires_approver_id() -> None:
    app = DatasetApproval(approver_id="  ")
    errs = validate_dataset_approval(app, owner_id="alice")
    assert errs
    assert "approver_id is required and must be non-empty" in errs


def test_owner_cannot_approve_own_dataset() -> None:
    app = DatasetApproval(approver_id="alice")
    errs = validate_dataset_approval(app, owner_id="alice")
    assert errs
    assert "owner cannot approve own dataset" in errs


def test_lineage_validates_against_matching_dataset_digest() -> None:
    rec = _base_record(
        dataset_id="ds-99",
        dataset_digest=f"sha256:{_HEX64}",
    )
    lin = DatasetLineageRef(dataset_id="ds-99", dataset_digest=_HEX64)
    assert validate_dataset_lineage(lin, record=rec) == ()


def test_lineage_fails_on_digest_mismatch() -> None:
    other = "b" * 64
    rec = _base_record(dataset_digest=_HEX64)
    lin = DatasetLineageRef(dataset_id="ds-1", dataset_digest=other)
    errs = validate_dataset_lineage(lin, record=rec)
    assert errs
    assert "lineage dataset_digest does not match dataset record" in errs


def test_unknown_status_fails() -> None:
    rec = _base_record(status="RETIRED")
    errs = validate_dataset_record(rec)
    assert errs
    assert "status is not a known dataset status" in errs


def test_deterministic_repeated_validation() -> None:
    rec = _base_record()
    a = validate_dataset_record(rec)
    b = validate_dataset_record(rec)
    assert a == b
    assert a == ()


def test_naive_approval_expiration_fails() -> None:
    app = DatasetApproval(approver_id="bob", expires_at=datetime(2030, 1, 1, 12, 0, 0))
    errs = validate_dataset_approval(app, owner_id="alice")
    assert errs
    assert "approval expiration must be timezone-aware UTC when present" in errs


def test_non_utc_timezone_aware_approval_expiration_fails() -> None:
    tz_plus_one = timezone(timedelta(hours=1))
    app = DatasetApproval(
        approver_id="bob",
        expires_at=datetime(2030, 1, 1, 13, 0, 0, tzinfo=tz_plus_one),
    )
    errs = validate_dataset_approval(app, owner_id="alice")
    assert errs
    assert "approval expiration must be timezone-aware UTC when present" in errs


def test_utc_approval_expiration_passes() -> None:
    app = DatasetApproval(
        approver_id="bob",
        expires_at=_utc(datetime(2030, 1, 1, 12, 0, 0)),
    )
    assert validate_dataset_approval(app, owner_id="alice") == ()
