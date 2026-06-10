#!/usr/bin/env python3
"""Record deterministic demo-flow evidence from MCP CLI (not Cursor UI screenshots)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
MCP = REPO / "mcp" / "aigov_mcp_server.py"
EVIDENCE = REPO / "examples" / "standards" / "governance_evidence_pack.valid.json"
OUT = REPO / ".cursor-plugin" / "assets" / "capture-evidence" / "demo-flow-evidence.json"
TIMEOUT = 600


def _run(argv: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        argv,
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        check=False,
    )
    parsed: Any = None
    try:
        parsed = json.loads((proc.stdout or "").strip() or "{}")
    except json.JSONDecodeError:
        parsed = None
    return {
        "argv": argv,
        "exit_code": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "parsed": parsed,
        "ok": proc.returncode == 0 and isinstance(parsed, dict) and bool(parsed.get("ok")),
    }


def main() -> int:
    py = sys.executable or "python3"
    if not MCP.is_file():
        print(f"missing MCP CLI: {MCP}", file=sys.stderr)
        return 1

    cases = [
        _run([py, str(MCP), "installation-check"]),
        _run([py, str(MCP), "govai-gate-reports"]),
        _run(
            [
                py,
                str(MCP),
                "govai-verify-evidence-pack",
                "--path",
                str(EVIDENCE.relative_to(REPO)),
            ]
        ),
        _run(
            [
                py,
                str(MCP),
                "govai-generate-audit-report-template",
                "--stem",
                "cursor-marketplace-demo-evidence",
                "--dry-run",
            ]
        ),
    ]

    payload = {
        "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "purpose": "Demo-flow evidence from repository CLI; not a substitute for Cursor UI screenshots.",
        "ok": all(c["ok"] for c in cases),
        "cases": [
            {
                "name": case["argv"][2] if len(case["argv"]) > 2 else "unknown",
                "ok": case["ok"],
                "exit_code": case["exit_code"],
            }
            for case in cases
        ],
        "details": cases,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"record_cursor_marketplace_demo_evidence: wrote {OUT.relative_to(REPO)} ok={payload['ok']}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
