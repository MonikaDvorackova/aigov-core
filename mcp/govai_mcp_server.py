#!/usr/bin/env python3
"""GovAI local MCP-style bridge: subprocess wrappers with JSON results.

- CLI: ``python mcp/govai_mcp_server.py <command> [options]``
- MCP stdio: ``python mcp/govai_mcp_server.py mcp-stdio`` (JSON-RPC over MCP framing)

Subprocesses always use explicit argv lists (never ``shell=True``). Default commands avoid
network I/O. Write-capable tool: ``govai_generate_audit_report_template`` (unless ``dry_run``).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Final, Mapping

_STDIO_MAX_CHARS: Final[int] = 256 * 1024

_TOOLS_READ_ONLY: Final[frozenset[str]] = frozenset(
    {
        "govai_check",
        "govai_verify_evidence_pack",
        "govai_gate_reports",
        "govai_make_gate",
        "govai_validate_functions_v2_pack",
    }
)
_TOOLS_WRITE: Final[frozenset[str]] = frozenset({"govai_generate_audit_report_template"})


def resolve_repo_root(start: Path | None = None) -> Path:
    """Locate repository root (directory containing ``.cursor-plugin/plugin.json``).

    Falls back to the parent of ``mcp/`` when the manifest is not found (e.g. sparse checkouts).
    """
    here = (start or Path(__file__)).resolve()
    candidates = [here.parent, *here.parents]
    for p in candidates:
        if (p / ".cursor-plugin" / "plugin.json").is_file():
            return p
        if (p / "rust" / "Cargo.toml").is_file() and (p / "mcp" / "govai_mcp_server.py").is_file():
            return p
    return here.parent


REPO_ROOT = resolve_repo_root()
PYTHON_DIR = REPO_ROOT / "python"
VENV_PY = PYTHON_DIR / ".venv" / "bin" / "python"
SCRIPTS_GATE = REPO_ROOT / "scripts" / "gate_reports.py"

_TIMEOUT_DEFAULT_S = 300
_TIMEOUT_GATE_REPORTS_S = 180
_TIMEOUT_VERIFY_EVIDENCE_S = 300
_TIMEOUT_MAKE_GATE_S = 900
_TIMEOUT_PYTEST_S = 7200


def _resolve_python_for_package() -> list[str]:
    """Prefer project venv interpreter so ``-m aigov_py`` resolves."""
    if VENV_PY.is_file():
        return [str(VENV_PY)]
    return [sys.executable or "python3"]


def _tool_access(tool: str) -> str:
    if tool in _TOOLS_WRITE:
        return "write"
    if tool in _TOOLS_READ_ONLY:
        return "read_only"
    return "unknown"


def _truncate(s: str) -> tuple[str, bool]:
    if len(s) <= _STDIO_MAX_CHARS:
        return s, False
    return s[:_STDIO_MAX_CHARS], True


def _run_subprocess(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout_s: float = _TIMEOUT_DEFAULT_S,
) -> dict[str, Any]:
    command = [str(x) for x in argv]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd) if cwd else str(REPO_ROOT),
            env=dict(os.environ) | (dict(env) if env else {}),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        out, out_trunc = _truncate((e.stdout or "") if isinstance(e.stdout, str) else "")
        err, err_trunc = _truncate((e.stderr or "") if isinstance(e.stderr, str) else "")
        return {
            "ok": False,
            "command": command,
            "exit_code": None,
            "stdout": out,
            "stderr": err,
            "stdout_truncated": out_trunc,
            "stderr_truncated": err_trunc,
            "duration_ms": duration_ms,
            "error": "timeout",
            "message": str(e),
        }
    except OSError as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        return {
            "ok": False,
            "command": command,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
            "duration_ms": duration_ms,
            "error": "os_error",
            "message": str(e),
        }
    duration_ms = int((time.monotonic() - t0) * 1000)
    raw_out = proc.stdout or ""
    raw_err = proc.stderr or ""
    out, out_trunc = _truncate(raw_out)
    err, err_trunc = _truncate(raw_err)
    return {
        "ok": proc.returncode == 0,
        "command": command,
        "exit_code": proc.returncode,
        "stdout": out,
        "stderr": err,
        "stdout_truncated": out_trunc,
        "stderr_truncated": err_trunc,
        "duration_ms": duration_ms,
    }


def tool_govai_check(pytest_extra: list[str] | None = None) -> dict[str, Any]:
    """Local repository test suite (``python -m pytest`` from ``python/``)."""
    pytest_extra = pytest_extra or []
    py = _resolve_python_for_package()
    argv = [*py, "-m", "pytest", "-q", *pytest_extra]
    body = _run_subprocess(argv, cwd=PYTHON_DIR, timeout_s=_TIMEOUT_PYTEST_S)
    body["tool"] = "govai_check"
    body["govai_access"] = _tool_access("govai_check")
    body["note"] = "Runs pytest in python/; not the hosted govai check HTTP verdict."
    return body


def tool_govai_verify_evidence_pack(path: str) -> dict[str, Any]:
    """Offline validation of a Governance Evidence Pack JSON/YAML file."""
    p = (REPO_ROOT / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
    try:
        p.relative_to(REPO_ROOT)
    except ValueError:
        return {
            "ok": False,
            "error": "path_outside_repo",
            "path": str(p),
            "tool": "govai_verify_evidence_pack",
            "govai_access": _tool_access("govai_verify_evidence_pack"),
            "command": [],
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
            "duration_ms": 0,
        }
    if not p.is_file():
        return {
            "ok": False,
            "error": "not_a_file",
            "path": str(p),
            "tool": "govai_verify_evidence_pack",
            "govai_access": _tool_access("govai_verify_evidence_pack"),
            "command": [],
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
            "duration_ms": 0,
        }
    py = _resolve_python_for_package()
    argv = [*py, "-m", "aigov_py.standards.cli", "validate-evidence-pack", str(p)]
    body = _run_subprocess(argv, cwd=PYTHON_DIR, timeout_s=_TIMEOUT_VERIFY_EVIDENCE_S)
    body["tool"] = "govai_verify_evidence_pack"
    body["govai_access"] = _tool_access("govai_verify_evidence_pack")
    body["path"] = str(p)
    return body


def tool_govai_gate_reports() -> dict[str, Any]:
    py = sys.executable or "python3"
    argv = [py, str(SCRIPTS_GATE)]
    body = _run_subprocess(argv, cwd=REPO_ROOT, timeout_s=_TIMEOUT_GATE_REPORTS_S)
    body["tool"] = "govai_gate_reports"
    body["govai_access"] = _tool_access("govai_gate_reports")
    return body


def tool_govai_validate_functions_v2_pack(rel_path: str) -> dict[str, Any]:
    py = sys.executable or "python3"
    script = REPO_ROOT / "scripts" / "validate_govai_functions_v2_pack.py"
    argv = [py, str(script), "--strict", rel_path]
    body = _run_subprocess(argv, cwd=REPO_ROOT, timeout_s=120.0)
    body["tool"] = "govai_validate_functions_v2_pack"
    body["govai_access"] = _tool_access("govai_validate_functions_v2_pack")
    body["path"] = rel_path
    return body


def tool_govai_make_gate() -> dict[str, Any]:
    body = _run_subprocess(["make", "gate"], cwd=REPO_ROOT, timeout_s=_TIMEOUT_MAKE_GATE_S)
    body["tool"] = "govai_make_gate"
    body["govai_access"] = _tool_access("govai_make_gate")
    return body


def _audit_template_markdown(safe: str) -> str:
    return (
        f"# Audit report: {safe}\n\n"
        "## Evaluation gate\n\n"
        "Describe automated checks, test scope, and pass/fail criteria for this change set.\n\n"
        "## Human approval gate\n\n"
        "List required human reviewers, policy sign-off, and any staged rollout approvals.\n\n"
        "## Risk assessment\n\n"
        "Identify user, safety, security, and operational risks; note mitigations and residual risk.\n\n"
        "## Rollback plan\n\n"
        "Document how to revert or disable the change, data migration rollback (if any), and communication steps.\n"
    )


def tool_govai_generate_audit_report_template(
    *, stem: str | None, force: bool, dry_run: bool
) -> dict[str, Any]:
    """Write ``docs/reports/<stem>.md`` with required audit headings (mutating unless dry_run)."""
    slug = stem or f"govai-audit-template-{uuid.uuid4().hex[:10]}"
    safe = "".join(c if c.isalnum() or c in {"-", "_"} else "-" for c in slug.strip().lower())
    reports = REPO_ROOT / "docs" / "reports"
    target = reports / f"{safe}.md"
    content = _audit_template_markdown(safe)

    if dry_run:
        return {
            "ok": True,
            "tool": "govai_generate_audit_report_template",
            "govai_access": "read_only",
            "dry_run": True,
            "wrote_file": False,
            "path": str(target),
            "would_write_bytes": len(content.encode("utf-8")),
            "preview": content[:1200],
            "command": [],
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
            "duration_ms": 0,
        }

    reports.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        return {
            "ok": False,
            "error": "file_exists",
            "path": str(target),
            "tool": "govai_generate_audit_report_template",
            "govai_access": _tool_access("govai_generate_audit_report_template"),
            "hint": "Pass --force to overwrite.",
            "dry_run": False,
            "wrote_file": False,
            "command": [],
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
            "duration_ms": 0,
        }
    target.write_text(content, encoding="utf-8")
    return {
        "ok": True,
        "path": str(target),
        "tool": "govai_generate_audit_report_template",
        "govai_access": _tool_access("govai_generate_audit_report_template"),
        "dry_run": False,
        "wrote_file": True,
        "command": [],
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "stdout_truncated": False,
        "stderr_truncated": False,
        "duration_ms": 0,
    }


_TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "govai_check",
        "description": "[read-only] Run local pytest suite (python -m pytest -q) from python/ using the project venv if present.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pytest_args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Extra pytest CLI arguments (optional).",
                }
            },
        },
    },
    {
        "name": "govai_verify_evidence_pack",
        "description": "[read-only] Offline validate a Governance Evidence Pack JSON/YAML file via aigov_py.standards.cli.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Repo-relative or absolute path to the document."}
            },
            "required": ["path"],
        },
    },
    {
        "name": "govai_gate_reports",
        "description": "[read-only] Run scripts/gate_reports.py (required markdown headings in docs/reports).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "govai_make_gate",
        "description": "[read-only] Run make gate (Makefile gate target).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "govai_validate_functions_v2_pack",
        "description": "[read-only] Validate a GovAI Functions 2.0 flight-pack JSON fixture (scripts/validate_govai_functions_v2_pack.py --strict).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Repo-relative path to JSON (e.g. examples/govai-functions-2/sample-flight-pack.v1.json).",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "govai_generate_audit_report_template",
        "description": "[write] Create docs/reports/<stem>.md with required audit sections. Use dry_run=true to preview without writing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "stem": {"type": "string"},
                "force": {"type": "boolean", "default": False},
                "dry_run": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, return preview only; do not write to disk.",
                },
            },
        },
    },
]


def _dispatch_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    arguments = arguments or {}
    if name == "govai_check":
        raw = arguments.get("pytest_args") or []
        extra = [str(x) for x in raw] if isinstance(raw, list) else []
        return tool_govai_check(extra)
    if name == "govai_verify_evidence_pack":
        path = str(arguments.get("path") or "").strip()
        if not path:
            return {
                "ok": False,
                "error": "missing_path",
                "tool": name,
                "govai_access": _tool_access(name),
                "command": [],
                "exit_code": None,
                "stdout": "",
                "stderr": "",
                "stdout_truncated": False,
                "stderr_truncated": False,
                "duration_ms": 0,
            }
        return tool_govai_verify_evidence_pack(path)
    if name == "govai_gate_reports":
        return tool_govai_gate_reports()
    if name == "govai_make_gate":
        return tool_govai_make_gate()
    if name == "govai_validate_functions_v2_pack":
        path = str(arguments.get("path") or "").strip()
        if not path:
            return {
                "ok": False,
                "error": "missing_path",
                "tool": name,
                "govai_access": _tool_access(name),
                "command": [],
                "exit_code": None,
                "stdout": "",
                "stderr": "",
                "stdout_truncated": False,
                "stderr_truncated": False,
                "duration_ms": 0,
            }
        return tool_govai_validate_functions_v2_pack(path)
    if name == "govai_generate_audit_report_template":
        stem = arguments.get("stem")
        stem_s = str(stem).strip() if stem else None
        force = bool(arguments.get("force"))
        dry_run = bool(arguments.get("dry_run"))
        return tool_govai_generate_audit_report_template(stem=stem_s, force=force, dry_run=dry_run)
    return {
        "ok": False,
        "error": "unknown_tool",
        "tool": name,
        "govai_access": "unknown",
        "command": [],
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "stdout_truncated": False,
        "stderr_truncated": False,
        "duration_ms": 0,
    }


def _write_mcp_message(obj: dict[str, Any]) -> None:
    raw = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii")
    sys.stdout.buffer.write(header + raw)
    sys.stdout.buffer.flush()


def _read_mcp_message() -> dict[str, Any] | None:
    line = sys.stdin.buffer.readline()
    if not line:
        return None
    if not line.lower().startswith(b"content-length:"):
        return None
    try:
        n = int(line.split(b":", 1)[1].strip())
    except (ValueError, IndexError):
        return None
    _ = sys.stdin.buffer.readline()
    body = sys.stdin.buffer.read(n)
    return json.loads(body.decode("utf-8"))


def run_mcp_stdio() -> int:
    """Minimal MCP server (tools only) over stdio Content-Length framing."""
    while True:
        msg = _read_mcp_message()
        if msg is None:
            return 0
        mid = msg.get("id")
        method = msg.get("method")
        params = msg.get("params") or {}

        if method == "initialize":
            _write_mcp_message(
                {
                    "jsonrpc": "2.0",
                    "id": mid,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "govai-local", "version": "0.1.0"},
                    },
                }
            )
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            _write_mcp_message(
                {
                    "jsonrpc": "2.0",
                    "id": mid,
                    "result": {"tools": _TOOL_SPECS},
                }
            )
        elif method == "tools/call":
            name = str((params.get("name") or "")).strip()
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            result = _dispatch_tool(name, arguments)
            _write_mcp_message(
                {
                    "jsonrpc": "2.0",
                    "id": mid,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}],
                        "isError": not bool(result.get("ok")),
                    },
                }
            )
        elif method == "ping":
            _write_mcp_message({"jsonrpc": "2.0", "id": mid, "result": {}})
        else:
            _write_mcp_message(
                {
                    "jsonrpc": "2.0",
                    "id": mid,
                    "error": {"code": -32601, "message": f"Method not found: {method!r}"},
                }
            )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="GovAI local MCP bridge")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_stdio = sub.add_parser("mcp-stdio", help="MCP JSON-RPC over stdio (Content-Length framing).")
    p_stdio.set_defaults(func=lambda _: run_mcp_stdio())

    p_check = sub.add_parser("govai-check", help="Run pytest in python/ (local check).")
    p_check.add_argument("pytest_arg", nargs="*", help="Extra args forwarded to pytest.")
    p_check.set_defaults(func=lambda ns: _emit(tool_govai_check(list(ns.pytest_arg))))

    p_vep = sub.add_parser("govai-verify-evidence-pack", help="Offline validate governance evidence pack file.")
    p_vep.add_argument("--path", required=True)
    p_vep.set_defaults(func=lambda ns: _emit(tool_govai_verify_evidence_pack(ns.path)))

    p_gr = sub.add_parser("govai-gate-reports", help="Run scripts/gate_reports.py.")
    p_gr.set_defaults(func=lambda _: _emit(tool_govai_gate_reports()))

    p_mg = sub.add_parser("govai-make-gate", help="Run make gate.")
    p_mg.set_defaults(func=lambda _: _emit(tool_govai_make_gate()))

    p_f2 = sub.add_parser(
        "govai-validate-functions-v2-pack",
        help="Validate GovAI Functions 2.0 flight-pack JSON (--strict).",
    )
    p_f2.add_argument("--path", required=True, help="Repo-relative JSON path")
    p_f2.set_defaults(func=lambda ns: _emit(tool_govai_validate_functions_v2_pack(ns.path)))

    p_tpl = sub.add_parser("govai-generate-audit-report-template", help="Write docs/reports/<stem>.md template.")
    p_tpl.add_argument("--stem", default=None, help="Filename stem (no extension).")
    p_tpl.add_argument("--force", action="store_true", help="Overwrite if exists.")
    p_tpl.add_argument("--dry-run", action="store_true", help="Print preview JSON only; do not write.")
    p_tpl.set_defaults(
        func=lambda ns: _emit(
            tool_govai_generate_audit_report_template(stem=ns.stem, force=ns.force, dry_run=ns.dry_run)
        )
    )

    ns = p.parse_args(argv)
    code: int = int(ns.func(ns))
    return code


def _emit(obj: dict[str, Any]) -> int:
    sys.stdout.write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    return 0 if obj.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
