#!/usr/bin/env python3
"""Validate reconstructible agent demo (structure, routes, scope, verdict semantics)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "rust/src/govai_api.rs"
DEMO_DIR = ROOT / "examples/reconstructible-agent-demo"

REQUIRED_PATHS = (
    DEMO_DIR / "run_demo.py",
    DEMO_DIR / "README.md",
    DEMO_DIR / "viewer/index.html",
    DEMO_DIR / "exports",
    ROOT / "docs/reconstructible-agent-demo.md",
    ROOT / "docs/reports/reconstructible-agent-demo.md",
)

SCAN_FILES = [
    DEMO_DIR / "run_demo.py",
    DEMO_DIR / "README.md",
    DEMO_DIR / "viewer/index.html",
    ROOT / "docs/reconstructible-agent-demo.md",
    ROOT / "docs/reports/reconstructible-agent-demo.md",
]

FORBIDDEN_TERMS = (
    "stripe",
    "billing",
    "pricing",
    "dashboard acl",
    "onboarding",
    "hosted saas",
    "platform entitlements",
    "kovali",
)

FORBIDDEN_PATH_LITERALS = (
    "/pricing",
    "/usage",
    "/verify-log",
    "/api/me",
    "/api/assessments",
    "/stripe",
    "/onboarding",
    "/api/compliance-workflow",
)

GOVAI_ROUTE_PREFIXES = (
    "/evidence",
    "/compliance-summary",
    "/verify",
    "/api/export",
    "/bundle-hash",
    "/bundle",
    "/health",
    "/ready",
    "/status",
)

ROUTE_RE = re.compile(r'\.route\("([^"]+)"')
HTTP_PATH_RE = re.compile(r'["\`]((?:GET|POST|PUT|PATCH|DELETE)\s+)?(/[a-zA-Z0-9_{}/:-]+)')
KOOVALI_RE = re.compile(r"\bkovali\b", re.IGNORECASE)

# Client-side verdict must come from ledger reads, not hardcoded compliance outcomes.
FAKE_VERDICT_RE = re.compile(
    r"(?:verdict\s*=\s*[\"'](?:VALID|INVALID|BLOCKED)[\"']"
    r"|return\s+[\"'](?:VALID|INVALID|BLOCKED)[\"']"
    r"|[\"']compliance_verdict[\"']\s*:\s*[\"'](?:VALID|INVALID|BLOCKED)[\"'])",
    re.IGNORECASE,
)

EXPORT_SAVE_RE = re.compile(r"exports\s*/\s*|save_export|/exports/")
VIEWER_EXPORT_RE = re.compile(r"exports/|export.*\.json|loadFromText|schema_version", re.IGNORECASE)


def load_mounted_from_router() -> set[str]:
    text = ROUTER.read_text(encoding="utf-8")
    paths = ROUTE_RE.findall(text)
    return {p.replace(":run_id", "{run_id}") for p in paths}


def path_allowed(path: str, mounted: set[str]) -> bool:
    if path in mounted:
        return True
    for template in mounted:
        if template.startswith(path + "/"):
            return True
    return False


def extract_http_paths(content: str) -> set[str]:
    found: set[str] = set()
    for m in HTTP_PATH_RE.finditer(content):
        path = m.group(2).split("?")[0].rstrip("/") or "/"
        path = path.replace(":run_id", "{run_id}")
        found.add(path)
    return found


def scan_routes(path: Path, mounted: set[str], failures: list[str]) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix not in {".py", ".md", ".html"}:
        return
    for forbidden in FORBIDDEN_PATH_LITERALS:
        if forbidden in text:
            failures.append(f"{path.relative_to(ROOT)}: forbidden platform path {forbidden!r}")
    for http_path in extract_http_paths(text):
        if any(http_path.startswith(fp) for fp in FORBIDDEN_PATH_LITERALS):
            continue
        if not any(http_path.startswith(p) for p in GOVAI_ROUTE_PREFIXES):
            continue
        if http_path == "/api/export":
            continue
        if http_path.startswith("/api/") and not http_path.startswith("/api/export"):
            failures.append(f"{path.relative_to(ROOT)}: non-core /api path {http_path!r}")
        elif http_path.startswith("/v1/"):
            failures.append(f"{path.relative_to(ROOT)}: preview/platform path {http_path!r}")
        elif not path_allowed(http_path, mounted):
            failures.append(f"{path.relative_to(ROOT)}: path {http_path!r} not mounted on aigov_audit")


def main() -> int:
    mounted = load_mounted_from_router()
    failures: list[str] = []

    for req in REQUIRED_PATHS:
        if not req.exists():
            failures.append(f"missing required path: {req.relative_to(ROOT)}")

    run_demo = DEMO_DIR / "run_demo.py"
    if run_demo.is_file():
        demo_text = run_demo.read_text(encoding="utf-8")
        if not EXPORT_SAVE_RE.search(demo_text):
            failures.append("run_demo.py: must save export under exports/")
        if FAKE_VERDICT_RE.search(demo_text):
            failures.append("run_demo.py: fake/hardcoded verdict semantics detected")
        if "verdict_from_summary" not in demo_text:
            failures.append("run_demo.py: must read verdict from compliance-summary/export")
        for route in ("/compliance-summary", "/api/export", "/verify"):
            if route not in demo_text:
                failures.append(f"run_demo.py: missing reference to mounted route {route}")

    viewer = DEMO_DIR / "viewer/index.html"
    if viewer.is_file():
        viewer_text = viewer.read_text(encoding="utf-8")
        if not VIEWER_EXPORT_RE.search(viewer_text):
            failures.append("viewer/index.html: must load replay from audit export JSON")
        if "log_chain" not in viewer_text:
            failures.append("viewer/index.html: must display hash chain / replay integrity")

    for path in SCAN_FILES:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lower = text.lower()
        if KOOVALI_RE.search(text):
            failures.append(f"{path.relative_to(ROOT)}: Kovali branding forbidden")
        for term in FORBIDDEN_TERMS:
            if term.lower() in lower:
                failures.append(f"{path.relative_to(ROOT)}: forbidden term {term!r}")
        scan_routes(path, mounted, failures)
        if path == run_demo and FAKE_VERDICT_RE.search(text):
            failures.append(f"{path.relative_to(ROOT)}: fake/hardcoded verdict semantics")

    doc = ROOT / "docs/reconstructible-agent-demo.md"
    if doc.is_file() and "append-only" not in doc.read_text(encoding="utf-8").lower():
        failures.append("docs/reconstructible-agent-demo.md: must explain append-only evidence")

    report = ROOT / "docs/reports/reconstructible-agent-demo.md"
    if report.is_file():
        report_text = report.read_text(encoding="utf-8")
        for heading in ("## Evaluation gate", "## Human approval gate", "## Replay semantics", "## Verification"):
            if heading not in report_text:
                failures.append(f"docs/reports/reconstructible-agent-demo.md: missing {heading}")

    if failures:
        print("reconstructible-demo-check failed:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print("reconstructible-demo-check passed.")
    print(f"Demo: examples/reconstructible-agent-demo/")
    print(f"Viewer: examples/reconstructible-agent-demo/viewer/index.html")
    print(f"Export dir: examples/reconstructible-agent-demo/exports/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
