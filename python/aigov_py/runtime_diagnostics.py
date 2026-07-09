"""Operator diagnostics against AIGov Core ``/health``, ``/ready``, and ``/status``."""

from __future__ import annotations

import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _get_json(url: str, *, timeout_sec: float) -> tuple[int, Any]:
    req = Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw.strip() else {}
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed: Any = json.loads(body) if body.strip() else {}
        except json.JSONDecodeError:
            parsed = {"raw": body[:500]}
        return e.code, parsed
    except URLError as e:
        raise RuntimeError(f"request failed: {e}") from e


def _print_block(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def _status_summary(status: dict[str, Any]) -> None:
    cfg = status.get("configuration") if isinstance(status.get("configuration"), dict) else {}
    comps = (
        status.get("readiness_components")
        if isinstance(status.get("readiness_components"), dict)
        else {}
    )
    print(f"runtime_version: {status.get('runtime_version', '?')}")
    print(f"environment: {status.get('environment', '?')}")
    print(f"policy_version: {status.get('policy_version', '?')}")
    print(f"uptime_seconds: {status.get('uptime_seconds', '?')}")
    print(f"operational_ready: {status.get('operational_ready', '?')}")
    print(f"ledger_dir_configured: {cfg.get('ledger_dir_configured', '?')}")
    print(f"ledger_dir_label: {cfg.get('ledger_dir_label', '?')}")
    print(f"database_configured: {cfg.get('database_configured', '?')}")
    print(f"policy_dir_configured: {cfg.get('policy_dir_configured', '?')}")
    print(f"signing_trust_configured: {cfg.get('signing_trust_configured', '?')}")
    print(f"api_key_allowlist_count: {cfg.get('api_key_allowlist_count', '?')}")
    print(f"migration_status: {comps.get('migration_status', '?')}")
    print(f"readiness_components: {json.dumps(comps, sort_keys=True)}")


def run_runtime_diagnostics(
    base_url: str,
    *,
    timeout_sec: float = 10.0,
    json_out: bool = False,
) -> int:
    """Probe health/ready/status and print operator-friendly output. Returns process exit code."""

    root = base_url.rstrip("/")
    report: dict[str, Any] = {"base_url": root, "checks": {}}
    ok_all = True

    for path in ("/health", "/ready", "/status"):
        url = f"{root}{path}"
        try:
            code, body = _get_json(url, timeout_sec=timeout_sec)
        except RuntimeError as e:
            report["checks"][path] = {"ok": False, "error": str(e)}
            ok_all = False
            continue
        passed = path == "/health" and code == 200 and isinstance(body, dict) and body.get("ok") is not False
        if path == "/ready":
            passed = code == 200 and isinstance(body, dict) and body.get("ready") is True
        if path == "/status":
            passed = code == 200 and isinstance(body, dict) and body.get("ok") is not False
        report["checks"][path] = {"ok": passed, "http_status": code, "body": body}
        if not passed:
            ok_all = False

    if json_out:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if ok_all else 1

    _print_block("GovAI runtime diagnostics")
    print(f"base_url: {root}")

    for path in ("/health", "/ready", "/status"):
        entry = report["checks"].get(path, {})
        label = "PASS" if entry.get("ok") else "FAIL"
        code = entry.get("http_status", "?")
        print(f"{label} {path} (HTTP {code})")
        if path == "/status" and isinstance(entry.get("body"), dict):
            _status_summary(entry["body"])

    return 0 if ok_all else 1


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="AIGov Core runtime diagnostics (health/ready/status).")
    p.add_argument(
        "--base-url",
        default=None,
        help="Audit service origin (default: GOVAI_AUDIT_BASE_URL or http://127.0.0.1:8088).",
    )
    p.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout seconds.")
    p.add_argument("--json", action="store_true", help="Emit machine-readable report on stdout.")
    args = p.parse_args(argv)

    import os

    base = (args.base_url or os.environ.get("GOVAI_AUDIT_BASE_URL") or "http://127.0.0.1:8088").strip()
    if not base:
        print("error: --base-url or GOVAI_AUDIT_BASE_URL required", file=sys.stderr)
        return 2
    try:
        return run_runtime_diagnostics(base, timeout_sec=args.timeout, json_out=args.json)
    except Exception as e:  # noqa: BLE001
        print(f"error: runtime-diagnostics failed: {e}", file=sys.stderr)
        return 1
