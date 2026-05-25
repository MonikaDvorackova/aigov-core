#!/usr/bin/env python3
"""Ensure adoption examples reference only routes mounted by aigov_audit."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "rust/src/govai_api.rs"

SCAN_PATHS = [
    ROOT / "examples/basic-runtime-client",
    ROOT / "examples/python-runtime-client",
    ROOT / "docs/quickstart-runtime.md",
    ROOT / "docs/runtime-api-contract.md",
]

# Documented platform routes that must not appear as live example calls.
FORBIDDEN_PATH_LITERALS = (
    "/pricing",
    "/usage",
    "/verify-log",
    "/metrics",
    "/api/me",
    "/api/assessments",
    "/api/compliance-workflow",
    "/stripe",
    "/onboarding",
)

# Normalized mounted templates (from build_router in govai_api.rs).
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


def load_mounted_from_router() -> list[str]:
    text = ROUTER.read_text(encoding="utf-8")
    paths = ROUTE_RE.findall(text)
    if not paths:
        raise RuntimeError(f"no .route(...) entries found in {ROUTER}")
    normalized: list[str] = []
    for p in paths:
        normalized.append(p.replace(":run_id", "{run_id}"))
    return sorted(set(normalized))


def extract_http_paths(content: str) -> set[str]:
    found: set[str] = set()
    for m in re.finditer(r'["\`]((?:GET|POST|PUT|PATCH|DELETE)\s+)?(/[a-zA-Z0-9_{}/:-]+)', content):
        path = m.group(2).split("?")[0].rstrip("/") or "/"
        path = path.replace(":run_id", "{run_id}")
        found.add(path)
    return found


def path_allowed(path: str, mounted: set[str]) -> bool:
    if path in mounted:
        return True
    # Allow referencing parent paths when child templates exist.
    for template in mounted:
        if template.startswith(path + "/"):
            return True
    return False


def main() -> int:
    mounted_list = load_mounted_from_router()
    mounted = set(mounted_list)
    if mounted != set(MOUNTED_TEMPLATES):
        print(
            "Warning: mounted route set changed; update MOUNTED_TEMPLATES in this script.",
            file=sys.stderr,
        )
        print(f"  router: {sorted(mounted)}", file=sys.stderr)
        print(f"  script: {sorted(MOUNTED_TEMPLATES)}", file=sys.stderr)

    failures: list[str] = []

    for forbidden in FORBIDDEN_PATH_LITERALS:
        for scan_root in SCAN_PATHS:
            if not scan_root.exists():
                continue
            files = [scan_root] if scan_root.is_file() else scan_root.rglob("*")
            for f in files:
                if f.is_dir():
                    continue
                if f.suffix not in {".sh", ".py"}:
                    continue
                text = f.read_text(encoding="utf-8", errors="replace")
                if forbidden in text:
                    failures.append(f"{f.relative_to(ROOT)}: references forbidden platform path {forbidden!r}")

    for scan_root in SCAN_PATHS:
        if not scan_root.exists():
            failures.append(f"missing scan path: {scan_root.relative_to(ROOT)}")
            continue
        files = [scan_root] if scan_root.is_file() else scan_root.rglob("*")
        for f in files:
            if f.is_dir():
                continue
            if f.suffix not in {".md", ".sh", ".py"}:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            for path in extract_http_paths(text):
                if any(path.startswith(fp) for fp in FORBIDDEN_PATH_LITERALS):
                    continue
                if path.startswith("/api/") and not path.startswith("/api/export/"):
                    failures.append(f"{f.relative_to(ROOT)}: non-core /api path {path!r}")
                elif path.startswith("/v1/"):
                    failures.append(f"{f.relative_to(ROOT)}: preview/platform path {path!r}")
                elif path.startswith("/") and not path_allowed(path, mounted):
                    failures.append(
                        f"{f.relative_to(ROOT)}: path {path!r} not mounted (allowed: {sorted(mounted)})"
                    )

    if failures:
        print("core-runtime-examples-check failed:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print("core-runtime-examples-check passed.")
    print(f"Mounted routes ({len(mounted)}): {', '.join(sorted(mounted))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
