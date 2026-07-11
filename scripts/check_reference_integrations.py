#!/usr/bin/env python3
"""Validate AIGov Core reference integration examples (structure, routes, scope)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "rust/src/govai_api.rs"

EXAMPLE_DIRS = (
    "openai-runtime-audit",
    "fastapi-runtime-middleware",
    "tool-call-audit",
    "human-approval-runtime",
)

SCAN_ROOTS = [ROOT / "examples" / d for d in EXAMPLE_DIRS]
SCAN_ROOTS.append(ROOT / "docs/reference-integrations.md")

FORBIDDEN_TERMS = (
    "stripe",
    "billing",
    "pricing",
    "dashboard acl",
    "onboarding",
    "hosted saas",
)

# Example app routes (not aigov_audit) — do not treat as HTTP contract drift.
APP_ROUTE_PREFIXES = ("/ai/",)

GOVAI_ROUTE_PREFIXES = (
    "/evidence",
    "/compliance-summary",
    "/verify",
    "/api/export",
    "/bundle",
    "/bundle-hash",
    "/health",
    "/ready",
    "/status",
)

FORBIDDEN_PATH_LITERALS = (
    "/pricing",
    "/usage",
    "/verify-log",
    "/metrics",
    "/api/me",
    "/api/assessments",
    "/stripe",
    "/onboarding",
)

MOUNTED_TEMPLATES = (
    "/",
    "/health",
    "/ready",
    "/status",
    "/evidence",
    "/bundle",
    "/bundle/{run_id}",
    "/bundle-hash",
    "/bundle-hash/{run_id}",
    "/compliance-summary",
    "/compliance-summary/{run_id}",
    "/api/export/{run_id}",
    "/verify",
    "/verify/{run_id}",
)

ROUTE_RE = re.compile(r'\.route\("([^"]+)"')
HTTP_PATH_RE = re.compile(r'["\`]((?:GET|POST|PUT|PATCH|DELETE)\s+)?(/[a-zA-Z0-9_{}/:-]+)')
KOOVALI_RE = re.compile(r"\bkovali\b", re.IGNORECASE)


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


def scan_file(path: Path, mounted: set[str], failures: list[str], *, examples_only_terms: bool) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    lower = text.lower()

    if KOOVALI_RE.search(text):
        failures.append(f"{path.relative_to(ROOT)}: uses Kovali branding (use GovAI)")

    if examples_only_terms:
        for term in FORBIDDEN_TERMS:
            if term.lower() in lower:
                failures.append(f"{path.relative_to(ROOT)}: mentions forbidden platform term {term!r}")

    if path.suffix not in {".md", ".py", ".sh"}:
        return

    if path.suffix in {".py", ".sh"}:
        for forbidden in FORBIDDEN_PATH_LITERALS:
            if forbidden in text:
                failures.append(f"{path.relative_to(ROOT)}: references forbidden platform path {forbidden!r}")

    for http_path in extract_http_paths(text):
        if any(http_path.startswith(fp) for fp in FORBIDDEN_PATH_LITERALS):
            continue
        if any(http_path.startswith(p) for p in APP_ROUTE_PREFIXES):
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
            failures.append(
                f"{path.relative_to(ROOT)}: path {http_path!r} not mounted on aigov_audit"
            )


def main() -> int:
    mounted = load_mounted_from_router()
    failures: list[str] = []

    for name in EXAMPLE_DIRS:
        ex_dir = ROOT / "examples" / name
        if not ex_dir.is_dir():
            failures.append(f"missing example directory: examples/{name}")
            continue
        readme = ex_dir / "README.md"
        if not readme.is_file():
            failures.append(f"missing README: examples/{name}/README.md")
        py_scripts = list(ex_dir.glob("*.py"))
        if not py_scripts:
            failures.append(f"no executable .py in examples/{name}")

    report = ROOT / "docs/reports/core-reference-integrations.md"
    if not report.is_file():
        failures.append("missing docs/reports/core-reference-integrations.md")

    doc = ROOT / "docs/reference-integrations.md"
    if not doc.is_file():
        failures.append("missing docs/reference-integrations.md")

    for scan_root in SCAN_ROOTS:
        if not scan_root.exists():
            failures.append(f"missing scan path: {scan_root.relative_to(ROOT)}")
            continue
        files = [scan_root] if scan_root.is_file() else scan_root.rglob("*")
        for f in files:
            if f.is_dir() or f.name.startswith("."):
                continue
            if f.suffix in {".pyc"} or "__pycache__" in f.parts:
                continue
            if f.suffix in {".md", ".py", ".sh"} or f.name == "README.md":
                examples_only = "examples" in f.parts and f.suffix in {".py", ".sh"}
                scan_file(f, mounted, failures, examples_only_terms=examples_only)

    common = ROOT / "examples/reference-runtime-common"
    if common.is_dir():
        for f in common.rglob("*.py"):
            scan_file(f, mounted, failures, examples_only_terms=True)

    if failures:
        print("reference-integrations-check failed:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print("reference-integrations-check passed.")
    print(f"Examples: {', '.join(EXAMPLE_DIRS)}")
    print(f"Mounted routes ({len(mounted)}): {', '.join(sorted(mounted))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
