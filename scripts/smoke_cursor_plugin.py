#!/usr/bin/env python3
"""Smoke-test AIGov Cursor MCP bridge with read-only CLI invocations.

Uses subprocess with explicit argv only (no shell). Exits non-zero on failure.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MCP_CLI = REPO_ROOT / "mcp" / "aigov_mcp_server.py"
EVIDENCE_PACK = REPO_ROOT / "examples" / "standards" / "governance_evidence_pack.valid.json"
SMOKE_TIMEOUT_SEC = 600


def _run(argv: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        argv,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=SMOKE_TIMEOUT_SEC,
        check=False,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _parse_json_stdout(stdout: str) -> dict[str, Any]:
    stdout = stdout.strip()
    if not stdout:
        raise ValueError("empty stdout")
    return json.loads(stdout)


def _case(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail}


def _mcp_request(proc: subprocess.Popen[str], payload: dict[str, Any]) -> dict[str, Any]:
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
    proc.stdin.flush()
    if "id" not in payload:
        return {}
    line = proc.stdout.readline()
    if not line.strip():
        raise ValueError("empty MCP stdout response")
    body = json.loads(line)
    if not isinstance(body, dict):
        raise ValueError("MCP response must be a JSON object")
    return body


def _smoke_mcp_stdio_handshake(py: str) -> tuple[bool, str]:
    proc = subprocess.Popen(
        [py, str(MCP_CLI), "mcp-stdio"],
        cwd=str(REPO_ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        init = _mcp_request(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "smoke", "version": "0.1.0"},
                },
            },
        )
        if "result" not in init:
            return False, f"initialize missing result keys={list(init.keys())}"
        if init["result"].get("serverInfo", {}).get("name") != "govai-local":
            return False, f"unexpected serverInfo={init['result'].get('serverInfo')}"

        _mcp_request(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _mcp_request(
            proc,
            {
                "jsonrpc": "2.0",
                "method": "notifications/cancelled",
                "params": {"requestId": 1, "reason": "smoke-test"},
            },
        )

        listed = _mcp_request(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = listed.get("result", {}).get("tools", [])
        names = {t.get("name") for t in tools if isinstance(t, dict)}
        expected = {
            "installation_check",
            "govai_gate_reports",
            "govai_verify_evidence_pack",
            "govai_generate_audit_report_template",
        }
        if names != expected:
            return False, f"tools/list names={sorted(names)}"
        return True, f"initialize ok; tools={len(tools)}"
    except (json.JSONDecodeError, ValueError, OSError) as e:
        return False, str(e)
    finally:
        if proc.stdin:
            proc.stdin.close()
        proc.wait(timeout=30)


def main() -> int:
    py = sys.executable or "python3"
    cases: list[dict[str, Any]] = []

    if not MCP_CLI.is_file():
        print(json.dumps({"ok": False, "error": "missing_mcp_cli", "path": str(MCP_CLI)}, indent=2))
        return 1
    if not EVIDENCE_PACK.is_file():
        print(json.dumps({"ok": False, "error": "missing_evidence_example", "path": str(EVIDENCE_PACK)}, indent=2))
        return 1

    ok_stdio, detail_stdio = _smoke_mcp_stdio_handshake(py)
    cases.append(_case("mcp-stdio handshake (initialize + tools/list)", ok_stdio, detail_stdio))

    # 1) govai-gate-reports
    argv_gr = [py, str(MCP_CLI), "govai-gate-reports"]
    code, out, _err = _run(argv_gr)
    try:
        body = _parse_json_stdout(out)
        ok_gr = code == 0 and bool(body.get("ok")) is True
        detail_gr = f"exit={code} ok={body.get('ok')}"
    except (json.JSONDecodeError, ValueError) as e:
        body = {}
        ok_gr = False
        detail_gr = f"exit={code} parse_error={e!s}"
    cases.append(_case("govai-gate-reports", ok_gr, detail_gr))

    # 2) govai-verify-evidence-pack
    rel = str(EVIDENCE_PACK.relative_to(REPO_ROOT))
    argv_vep = [py, str(MCP_CLI), "govai-verify-evidence-pack", "--path", rel]
    code, out, _err = _run(argv_vep)
    try:
        body_vep = _parse_json_stdout(out)
        ok_vep = code == 0 and bool(body_vep.get("ok")) is True
        detail_vep = f"exit={code} ok={body_vep.get('ok')}"
    except (json.JSONDecodeError, ValueError) as e:
        ok_vep = False
        detail_vep = f"exit={code} parse_error={e!s}"
    cases.append(_case("govai-verify-evidence-pack", ok_vep, detail_vep))

    # 3) audit template dry-run (no disk write)
    argv_dr = [
        py,
        str(MCP_CLI),
        "govai-generate-audit-report-template",
        "--stem",
        "smoke-cursor-plugin-dry-run",
        "--dry-run",
    ]
    code, out, _err = _run(argv_dr)
    try:
        body_dr = _parse_json_stdout(out)
        ok_dr = (
            code == 0
            and bool(body_dr.get("ok")) is True
            and bool(body_dr.get("dry_run")) is True
            and not bool(body_dr.get("wrote_file"))
        )
        detail_dr = f"exit={code} dry_run={body_dr.get('dry_run')} wrote_file={body_dr.get('wrote_file')}"
    except (json.JSONDecodeError, ValueError) as e:
        ok_dr = False
        detail_dr = f"exit={code} parse_error={e!s}"
    cases.append(_case("govai-generate-audit-report-template (dry-run)", ok_dr, detail_dr))

    overall = all(c["status"] == "pass" for c in cases)
    summary = {
        "ok": overall,
        "cases": cases,
        "repo_root": str(REPO_ROOT),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
