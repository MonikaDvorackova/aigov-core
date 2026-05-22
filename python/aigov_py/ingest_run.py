from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from aigov_py.env_resolution import resolve_aigov_environment
from aigov_py.run_rows import upsert_run_row
from aigov_py.supabase_db import create_supabase_client
from aigov_py.storage_upload import upload_artifacts_for_run


@dataclass(frozen=True)
class ArtifactPaths:
    repo_root: Path
    audit_json: Path
    evidence_json: Path
    report_md: Path
    pack_zip: Path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root_from_here() -> Path:
    p = Path(__file__).resolve()
    return p.parents[2]


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _sha256_file(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return None


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def _get_mode() -> str:
    v = os.environ.get("AIGOV_MODE", "").strip().lower()
    return v or "ci"


def _artifact_paths(run_id: str) -> ArtifactPaths:
    root = _repo_root_from_here()
    return ArtifactPaths(
        repo_root=root,
        audit_json=root / "docs" / "audit" / f"{run_id}.json",
        evidence_json=root / "docs" / "evidence" / f"{run_id}.json",
        report_md=root / "docs" / "reports" / f"{run_id}.md",
        pack_zip=root / "docs" / "packs" / f"{run_id}.zip",
    )


def _extract_bundle_sha256(audit_obj: Optional[Dict[str, Any]]) -> Optional[str]:
    if not audit_obj:
        return None

    for k in ("bundle_sha256", "bundleSha256"):
        v = audit_obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    bundle = audit_obj.get("bundle")
    if isinstance(bundle, dict):
        for k in ("sha256", "bundle_sha256", "bundleSha256", "hash"):
            v = bundle.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

    meta = audit_obj.get("meta")
    if isinstance(meta, dict):
        for k in ("bundle_sha256", "bundleSha256"):
            v = meta.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

    return None


def _extract_policy_version(audit_obj: Optional[Dict[str, Any]]) -> Optional[str]:
    if not audit_obj:
        return None

    for k in ("policy_version", "policyVersion"):
        v = audit_obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    policy = audit_obj.get("policy")
    if isinstance(policy, dict):
        for k in ("version", "policy_version", "policyVersion"):
            v = policy.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

    meta = audit_obj.get("meta")
    if isinstance(meta, dict):
        for k in ("policy_version", "policyVersion"):
            v = meta.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

    verification = audit_obj.get("verification")
    if isinstance(verification, dict):
        for k in ("policy_version", "policyVersion"):
            v = verification.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

    return None


def _extract_verdict_status(audit_obj: Optional[Dict[str, Any]]) -> Optional[str]:
    if not audit_obj:
        return None

    for k in ("verdict", "status", "verification_status", "verificationStatus"):
        v = audit_obj.get(k)
        if isinstance(v, str) and v.strip():
            vv = _norm(v)
            if vv in ("valid", "invalid", "pending"):
                return vv

    result = audit_obj.get("result")
    if isinstance(result, dict):
        v = result.get("verdict") or result.get("status")
        if isinstance(v, str) and v.strip():
            vv = _norm(v)
            if vv in ("valid", "invalid", "pending"):
                return vv

    return None


def _evidence_source(mode: str) -> str:
    m = _norm(mode)
    if m == "ci":
        return "ci_fallback"
    if m == "prod":
        return "prod"
    return m or "ci"


def _should_upload_to_storage(mode: str) -> bool:
    raw = os.environ.get("AIGOV_STORAGE_UPLOAD", "").strip().lower()
    if raw in ("1", "true", "yes", "y", "on"):
        return True
    if raw in ("0", "false", "no", "n", "off"):
        return False

    m = _norm(mode)
    return m in ("ci", "prod")


def build_run_row(run_id: str) -> Dict[str, Any]:
    mode = _get_mode()
    environment = resolve_aigov_environment()
    paths = _artifact_paths(run_id)

    audit_obj = _read_json(paths.audit_json)

    bundle_sha = _extract_bundle_sha256(audit_obj)
    policy_version = _extract_policy_version(audit_obj)
    status = _extract_verdict_status(audit_obj)

    evidence_sha = _sha256_file(paths.evidence_json)
    report_sha = _sha256_file(paths.report_md)

    if not bundle_sha:
        bundle_sha = _sha256_file(paths.pack_zip)

    if not policy_version:
        m = _norm(mode)
        env = _norm(environment)
        if env == "prod" and m == "prod":
            policy_version = "v0.5_prod"
        elif env == "staging":
            policy_version = "v0.5_staging"
        else:
            policy_version = "v0.5_dev"

    if not status:
        status = "valid" if _norm(mode) == "ci" else "pending"

    row: Dict[str, Any] = {
        "id": run_id,
        "created_at": _utc_now_iso(),
        "mode": mode,
        "status": status,
        "policy_version": policy_version,
        "bundle_sha256": bundle_sha,
        "evidence_sha256": evidence_sha,
        "report_sha256": report_sha,
        "evidence_source": _evidence_source(mode),
        "closed_at": _utc_now_iso(),
        "environment": environment,
    }

    return row


def upload_run_artifacts(run_id: str, mode: str) -> None:
    if not _should_upload_to_storage(mode):
        print("storage upload skipped")
        return

    client = create_supabase_client(strict=True)
    paths = _artifact_paths(run_id)

    results = upload_artifacts_for_run(
        client,
        run_id=run_id,
        pack_zip=paths.pack_zip,
        audit_json=paths.audit_json,
        evidence_json=paths.evidence_json,
    )

    ok_all = True
    for r in results:
        if r.ok:
            print(f"storage upload ok bucket={r.bucket} object={r.object_name}")
        else:
            ok_all = False
            print(f"storage upload failed bucket={r.bucket} object={r.object_name} error={r.message}")

    if not ok_all:
        raise RuntimeError("storage upload failed for one or more artifacts")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python -m aigov_py.ingest_run <RUN_ID>", file=sys.stderr)
        return 2

    run_id = argv[1].strip()
    if not run_id:
        print("RUN_ID is required", file=sys.stderr)
        return 2

    row = build_run_row(run_id)

    print("ROW BEING UPSERTED:")
    print(row)

    upsert_run_row(row)

    mode = str(row.get("mode") or _get_mode())
    upload_run_artifacts(run_id, mode)

    print(f"ingested run {run_id} (run metadata per AIGOV_RUN_PERSISTENCE)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
