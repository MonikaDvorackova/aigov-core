#!/usr/bin/env python3
"""Stdlib HTTP helpers for reference integration examples (mounted aigov_audit routes only)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT / "python") not in sys.path:
    sys.path.insert(0, str(_ROOT / "python"))

from aigov_py.runtime import RuntimeGovernanceClient
from aigov_py.runtime.models import EvidenceEvent


def env_config() -> dict[str, str | None]:
    return {
        "base": os.environ.get("GOVAI_AUDIT_BASE_URL", "http://127.0.0.1:8088").rstrip("/"),
        "api_key": (os.environ.get("GOVAI_API_KEY") or "").strip() or None,
        "run_id": os.environ.get("GOVAI_RUN_ID") or f"ref-{os.getpid()}",
        "project": (os.environ.get("GOVAI_PROJECT") or "").strip() or None,
        "timeout": float(os.environ.get("GOVAI_HTTP_TIMEOUT_SEC", "30")),
    }


def require_api_key() -> str:
    key = (os.environ.get("GOVAI_API_KEY") or "").strip()
    if not key:
        print(
            "GOVAI_API_KEY is required (must match GOVAI_API_KEYS / GOVAI_API_KEYS_JSON on the server).",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return key


def client_from_env() -> RuntimeGovernanceClient:
    cfg = env_config()
    if not cfg["api_key"]:
        require_api_key()
    return RuntimeGovernanceClient(
        str(cfg["base"]),
        api_key=str(cfg["api_key"]),
        project=cfg["project"],
        timeout_sec=float(cfg["timeout"]),
    )


def _join(base: str, path: str) -> str:
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def auth_headers(api_key: str, project: str | None = None) -> dict[str, str]:
    headers = {"Accept": "application/json", "Authorization": f"Bearer {api_key}"}
    if project:
        headers["X-GovAI-Project"] = project
    return headers


def get_json(url: str, headers: dict[str, str], timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    out = json.loads(body)
    if not isinstance(out, dict):
        raise RuntimeError(f"expected JSON object from {url}")
    return out


def post_evidence_dict(client: RuntimeGovernanceClient, wire: dict[str, Any], *, timeout: float) -> dict[str, Any]:
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
    result = client.submit_evidence(event, timeout_sec=timeout)
    return dict(result.raw)


def read_run(
    *,
    base: str,
    api_key: str,
    run_id: str,
    project: str | None,
    timeout: float,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    headers = auth_headers(api_key, project)
    summary = get_json(_join(base, f"/compliance-summary/{run_id}"), headers, timeout)
    export = get_json(_join(base, f"/api/export/{run_id}"), headers, timeout)
    verify = get_json(_join(base, f"/verify/{run_id}"), headers, timeout)
    return summary, export, verify


def print_json(label: str, doc: dict[str, Any]) -> None:
    print(f"\n== {label} ==")
    print(json.dumps(doc, indent=2))


def execute_guard() -> bool:
    if os.environ.get("GOVAI_EXAMPLE_EXECUTE") != "1":
        print("Dry run: set GOVAI_EXAMPLE_EXECUTE=1 to call the live runtime.", file=sys.stderr)
        return False
    return True
