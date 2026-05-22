from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UploadResult:
    ok: bool
    bucket: str
    object_name: str
    message: str


def _as_upsert_dict() -> dict:
    # supabase py expects file_options, keys vary across versions
    # keep both common spellings to maximize compatibility
    return {
        "upsert": "true",
        "x-upsert": "true",
    }


def upload_file_bytes(
    client,
    *,
    bucket: str,
    object_name: str,
    data: bytes,
    content_type: str,
) -> UploadResult:
    try:
        storage = client.storage.from_(bucket)

        # try upload with upsert enabled
        res = storage.upload(
            object_name,
            data,
            file_options={
                "content-type": content_type,
                **_as_upsert_dict(),
            },
        )

        # different client versions return different shapes
        if getattr(res, "error", None):
            err = res.error
            msg = getattr(err, "message", None) or str(err)
            return UploadResult(ok=False, bucket=bucket, object_name=object_name, message=msg)

        return UploadResult(ok=True, bucket=bucket, object_name=object_name, message="uploaded")

    except Exception as e:
        return UploadResult(ok=False, bucket=bucket, object_name=object_name, message=str(e))


def upload_file_path(
    client,
    *,
    bucket: str,
    object_name: str,
    path: Path,
    content_type: str,
) -> UploadResult:
    if not path.exists():
        return UploadResult(
            ok=False,
            bucket=bucket,
            object_name=object_name,
            message=f"file not found: {path}",
        )

    data = path.read_bytes()
    return upload_file_bytes(
        client,
        bucket=bucket,
        object_name=object_name,
        data=data,
        content_type=content_type,
    )


def upload_artifacts_for_run(
    client,
    *,
    run_id: str,
    pack_zip: Path,
    audit_json: Path,
    evidence_json: Path,
) -> list[UploadResult]:
    results: list[UploadResult] = []

    results.append(
        upload_file_path(
            client,
            bucket="packs",
            object_name=f"{run_id}.zip",
            path=pack_zip,
            content_type="application/zip",
        )
    )

    results.append(
        upload_file_path(
            client,
            bucket="audit",
            object_name=f"{run_id}.json",
            path=audit_json,
            content_type="application/json",
        )
    )

    results.append(
        upload_file_path(
            client,
            bucket="evidence",
            object_name=f"{run_id}.json",
            path=evidence_json,
            content_type="application/json",
        )
    )

    return results
