#!/usr/bin/env python3
"""Exercise mounted aigov_audit routes: evidence, summary, export, verify."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "python"))

from aigov_py.runtime import RuntimeGovernanceClient
from aigov_py.runtime.models import EvidenceEvent


def _join(base: str, path: str) -> str:
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def _get_json(url: str, headers: dict[str, str], timeout: float) -> dict:
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    out = json.loads(body)
    if not isinstance(out, dict):
        raise RuntimeError(f"expected JSON object from {url}")
    return out


def main() -> None:
    base = os.environ.get("GOVAI_AUDIT_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
    api_key = (os.environ.get("GOVAI_API_KEY") or "").strip()
    if not api_key:
        print("GOVAI_API_KEY is required.", file=sys.stderr)
        sys.exit(1)
    run_id = os.environ.get("GOVAI_RUN_ID", f"py-smoke-{os.getpid()}")
    project = (os.environ.get("GOVAI_PROJECT") or "").strip() or None
    timeout = float(os.environ.get("GOVAI_HTTP_TIMEOUT_SEC", "30"))

    fixture_path = _ROOT / "examples/basic-runtime-client/fixtures/discovery-event.json"
    wire = json.loads(fixture_path.read_text(encoding="utf-8"))
    wire["run_id"] = run_id
    wire["event_id"] = os.environ.get("GOVAI_EVENT_ID", f"{run_id}-discovery")

    client = RuntimeGovernanceClient(base, api_key=api_key, project=project, timeout_sec=timeout)
    event = EvidenceEvent(
        event_id=wire["event_id"],
        event_type=wire["event_type"],
        ts_utc=wire["ts_utc"],
        actor=wire["actor"],
        system=wire["system"],
        run_id=wire["run_id"],
        payload=wire["payload"],
        environment=wire.get("environment"),
    )

    print(f"base_url={base}")
    print(f"run_id={run_id}")
    print()

    print("-> POST /evidence")
    ingest = client.submit_evidence(event, timeout_sec=timeout)
    print(json.dumps(dict(ingest.raw), indent=2))

    print(f"\n-> GET /compliance-summary/{run_id}")
    summary = client.get_compliance_summary(run_id, timeout_sec=timeout)
    print(json.dumps(dict(summary.raw), indent=2))
    if summary.verdict is None:
        raise RuntimeError("compliance summary missing verdict")

    headers: dict[str, str] = {"Accept": "application/json", "Authorization": f"Bearer {api_key}"}
    if project:
        headers["X-GovAI-Project"] = project
    print(f"\n-> GET /api/export/{run_id}")
    export = _get_json(_join(base, f"/api/export/{run_id}"), headers, timeout)
    print(json.dumps(export, indent=2))
    if export.get("schema_version") != "aigov.audit_export.v1":
        raise RuntimeError("unexpected export schema_version")

    print(f"\n-> GET /verify/{run_id}")
    verify = _get_json(_join(base, f"/verify/{run_id}"), headers, timeout)
    print(json.dumps(verify, indent=2))
    if verify.get("ok") is not True:
        raise RuntimeError(f"verify failed: {verify}")

    print("\nSmoke finished successfully.")


if __name__ == "__main__":
    main()
