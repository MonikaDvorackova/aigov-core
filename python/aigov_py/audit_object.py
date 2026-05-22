from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from aigov_py.canonical_json import canonical_bytes


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_bytes(p: Path) -> bytes:
    return p.read_bytes()


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _load_json(p: Path) -> Dict[str, Any]:
    return json.loads(_read_text(p))


@dataclass(frozen=True)
class AuditObject:
    run_id: str
    policy_version: str
    bundle_sha256: str
    evidence_file_sha256: str
    report_file_sha256: str
    model_artifact_sha256: str | None
    log_path: str | None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "run_id": self.run_id,
            "policy_version": self.policy_version,
            "bundle_sha256": self.bundle_sha256,
            "evidence_file_sha256": self.evidence_file_sha256,
            "report_file_sha256": self.report_file_sha256,
            "model_artifact_sha256": self.model_artifact_sha256,
            "log_path": self.log_path,
            "schema": "aigov.audit_object.v1",
        }
        return d


def main() -> None:
    run_id = os.environ.get("RUN_ID", "").strip()
    if not run_id:
        raise SystemExit("RUN_ID is required. Usage: RUN_ID=<run_id> python -m aigov_py.audit_object")

    repo_root = Path(__file__).resolve().parents[2]

    evidence_path = repo_root / "docs" / "evidence" / f"{run_id}.json"
    report_path = repo_root / "docs" / "reports" / f"{run_id}.md"

    if not evidence_path.exists():
        raise SystemExit(f"evidence bundle not found: {evidence_path}")
    if not report_path.exists():
        raise SystemExit(f"audit report not found: {report_path}")

    bundle = _load_json(evidence_path)

    policy_version = str(bundle.get("policy_version", "")).strip()
    if not policy_version:
        raise SystemExit("evidence bundle missing policy_version")

    bundle_sha256 = str(bundle.get("bundle_sha256", "")).strip()
    if not bundle_sha256 or len(bundle_sha256) != 64:
        raise SystemExit("evidence bundle missing bundle_sha256")

    evidence_bytes = _read_bytes(evidence_path)
    report_bytes = _read_bytes(report_path)

    evidence_file_sha256 = _sha256_hex(evidence_bytes)
    report_file_sha256 = _sha256_hex(report_bytes)

    model_artifact_sha256: str | None = None
    artifact_path = bundle.get("model_artifact_path")
    if isinstance(artifact_path, str) and artifact_path.strip():
        artifact_fs_path = repo_root / artifact_path
        if artifact_fs_path.exists():
            model_artifact_sha256 = _sha256_hex(_read_bytes(artifact_fs_path))
        else:
            # keep None, but do not fail hard
            model_artifact_sha256 = None

    log_path: str | None = None
    lp = bundle.get("log_path")
    if isinstance(lp, str) and lp.strip():
        log_path = lp.strip()

    ao = AuditObject(
        run_id=run_id,
        policy_version=policy_version,
        bundle_sha256=bundle_sha256,
        evidence_file_sha256=evidence_file_sha256,
        report_file_sha256=report_file_sha256,
        model_artifact_sha256=model_artifact_sha256,
        log_path=log_path,
    )

    out_dir = repo_root / "docs" / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{run_id}.json"
    out_path.write_bytes(canonical_bytes(ao.to_dict()))

    print(f"saved {out_path}")


if __name__ == "__main__":
    main()
