"""
Write `.aigov_ci_artifacts/evidence_digest_manifest.json` from GET /bundle-hash (local CI audit).

Designed for artifact-bound continuity: downstream hosted gate compares `events_content_sha256`
against the hosted ledger after replay.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Write evidence_digest_manifest.json from GovAI bundle-hash.")
    p.add_argument("--run-id", required=True)
    p.add_argument(
        "--audit-url",
        default=os.environ.get("AUDIT_URL") or os.environ.get("GOVAI_AUDIT_BASE_URL") or "http://127.0.0.1:8088",
    )
    p.add_argument(
        "--out-dir",
        default=os.environ.get("AIGOV_ARTIFACT_DIR", ""),
        help="Directory for evidence_digest_manifest.json (required unless AIGOV_ARTIFACT_DIR)",
    )
    p.add_argument(
        "--api-key",
        default=os.environ.get("GOVAI_API_KEY") or "ci-test-api-key",
        help="Bearer token for local/hosted CI audit",
    )
    p.add_argument(
        "--project",
        default=os.environ.get("GOVAI_PROJECT") or "github-actions",
        help="X-GovAI-Project header",
    )
    args = p.parse_args(argv)

    run_id = args.run_id.strip()
    if not run_id:
        print("ERROR: empty run-id", file=sys.stderr)
        return 2

    out_dir_raw = str(args.out_dir or "").strip()
    if not out_dir_raw:
        print("ERROR: --out-dir or AIGOV_ARTIFACT_DIR is required", file=sys.stderr)
        return 2
    out_dir = Path(out_dir_raw)
    out_dir.mkdir(parents=True, exist_ok=True)

    base = str(args.audit_url).rstrip("/")
    url = f"{base}/bundle-hash?run_id={quote(run_id, safe='')}"
    headers: dict[str, str] = {"Accept": "application/json"}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"
    if args.project:
        headers["X-GovAI-Project"] = str(args.project)

    r = requests.get(url, headers=headers, timeout=30)
    if not r.ok:
        print(f"ERROR: bundle-hash HTTP {r.status_code}: {r.text[:2000]}", file=sys.stderr)
        return 1

    data: Any = r.json()
    if not isinstance(data, dict) or data.get("ok") is not True:
        print(f"ERROR: bundle-hash not ok: {data}", file=sys.stderr)
        return 1

    digest = data.get("events_content_sha256")
    if not isinstance(digest, str) or len(digest.strip()) != 64:
        print(
            "ERROR: bundle-hash response missing events_content_sha256 (upgrade aigov_audit / "
            "refuse unsafe gate).",
            file=sys.stderr,
        )
        return 1

    manifest = {
        "schema": "aigov.evidence_digest_manifest.v1",
        "run_id": run_id,
        "events_content_sha256": digest.strip().lower(),
        "evidence_digest_schema": str(data.get("evidence_digest_schema") or "aigov.evidence_digest.v1"),
        "bundle_sha256": str(data.get("bundle_sha256") or ""),
        "policy_version": str(data.get("policy_version") or ""),
    }

    out_path = out_dir / "evidence_digest_manifest.json"
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
