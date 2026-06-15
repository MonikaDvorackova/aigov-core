"""
Build ``aigov.audit_export_bundle.v1`` zip bundles for offline verification demos.

Digest rules match ``rust/src/audit_export_bundle.rs`` (canonical JSON, files sorted by path).
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

from aigov_py.canonical_json import canonical_bytes

BUNDLE_SCHEMA_V1 = "aigov.audit_export_bundle.v1"
DEFAULT_MANIFEST_PATH = "manifest.json"
DEFAULT_AUDIT_EXPORT_PATH = "audit_export.json"


def sha256_content_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def manifest_for_digest(manifest: dict[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in manifest.items() if k != "canonical_bundle_digest_sha256"}
    files = list(body.get("files") or [])
    files.sort(key=lambda item: str(item.get("path") or ""))
    body["files"] = files
    return body


def compute_canonical_bundle_digest(manifest: dict[str, Any]) -> str:
    return sha256_content_hex(canonical_bytes(manifest_for_digest(manifest)))


def finalize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    out = dict(manifest)
    out["schema_version"] = out.get("schema_version") or BUNDLE_SCHEMA_V1
    out["canonical_bundle_digest_sha256"] = compute_canonical_bundle_digest(out)
    return out


def build_manifest_json(manifest: dict[str, Any]) -> bytes:
    finalized = finalize_manifest(manifest)
    return (json.dumps(finalized, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def pack_bundle(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for path in sorted(entries):
            zf.writestr(path, entries[path])
    return buf.getvalue()


def write_bundle_zip(path: str | Path, entries: dict[str, bytes]) -> None:
    Path(path).write_bytes(pack_bundle(entries))


__all__ = [
    "BUNDLE_SCHEMA_V1",
    "DEFAULT_AUDIT_EXPORT_PATH",
    "DEFAULT_MANIFEST_PATH",
    "build_manifest_json",
    "compute_canonical_bundle_digest",
    "finalize_manifest",
    "pack_bundle",
    "sha256_content_hex",
    "write_bundle_zip",
]
