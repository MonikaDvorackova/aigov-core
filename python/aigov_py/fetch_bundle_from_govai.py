from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict
from urllib.parse import quote

import requests


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _evidence_path(run_id: str) -> Path:
    return _repo_root() / "docs" / "evidence" / f"{run_id}.json"


def audit_base_url() -> str:
    """Resolve GovAI audit base URL consistently with write_digest_manifest / Makefile defaults."""
    return (
        os.environ.get("AIGOV_AUDIT_ENDPOINT")
        or os.environ.get("AIGOV_AUDIT_URL")
        or os.environ.get("GOVAI_AUDIT_BASE_URL")
        or os.environ.get("AUDIT_URL")
        or "http://127.0.0.1:8088"
    ).rstrip("/")


def _request_headers() -> Dict[str, str]:
    """Headers for authenticated tenant-scoped bundle export (matches CI curl defaults)."""
    h: Dict[str, str] = {"Accept": "application/json"}
    key = (os.environ.get("GOVAI_API_KEY") or "ci-test-api-key").strip()
    if key:
        h["Authorization"] = f"Bearer {key}"
    proj = (os.environ.get("GOVAI_PROJECT") or "github-actions").strip()
    if proj:
        h["X-GovAI-Project"] = proj
    return h


def _get_json(url: str, *, what: str) -> Dict[str, Any]:
    try:
        r = requests.get(url, headers=_request_headers(), timeout=15)
        body = (r.text or "")[:4000]
        if not r.ok:
            print(
                f"::error::{what}: HTTP {r.status_code} GET {url!r}\n{body}",
                file=sys.stderr,
            )
            r.raise_for_status()
        try:
            return r.json()
        except ValueError as e:
            print(f"::error::{what}: invalid JSON from GET {url!r}\n{body}", file=sys.stderr)
            raise SystemExit(1) from e
    except requests.RequestException as e:
        print(f"::error::{what}: request failed GET {url!r}: {e}", file=sys.stderr)
        resp = getattr(e, "response", None)
        if resp is not None and getattr(resp, "text", None):
            print((resp.text or "")[:4000], file=sys.stderr)
        raise SystemExit(1) from e


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        raise SystemExit("Usage: python -m aigov_py.fetch_bundle_from_govai <run_id>")

    run_id = argv[1].strip()
    if not run_id:
        raise SystemExit("run_id is required")

    endpoint = audit_base_url()
    q = quote(run_id, safe="")
    bundle_url = f"{endpoint}/bundle?run_id={q}"
    digest_url = f"{endpoint}/bundle-hash?run_id={q}"

    bundle = _get_json(bundle_url, what="fetch_bundle_from_govai /bundle")
    if not bundle.get("ok"):
        print(f"::error::bundle JSON ok=false: {bundle}", file=sys.stderr)
        raise SystemExit(1)

    digest = _get_json(digest_url, what="fetch_bundle_from_govai /bundle-hash")
    if not digest.get("ok"):
        raise SystemExit(f"bundle-hash fetch failed: {digest}")

    bundle_sha256 = digest.get("bundle_sha256", "")
    if not isinstance(bundle_sha256, str) or not bundle_sha256.strip():
        raise SystemExit(f"bundle-hash missing bundle_sha256: {digest}")

    bundle["bundle_sha256"] = bundle_sha256

    out_path = _evidence_path(run_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"saved evidence bundle: {out_path}")


if __name__ == "__main__":
    main(sys.argv)

