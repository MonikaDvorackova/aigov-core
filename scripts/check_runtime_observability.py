#!/usr/bin/env python3
"""Validate runtime observability docs, routes, and scope."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "rust/src/govai_api.rs"

REQUIRED_PATHS = (
    ROOT / "docs/runtime-observability.md",
    ROOT / "docs/operator-diagnostics.md",
    ROOT / "docs/reports/runtime-observability-diagnostics.md",
    ROOT / "python/aigov_py/runtime_diagnostics.py",
    ROOT / "python/aigov_py/trace_context.py",
    ROOT / "rust/src/runtime_diagnostics.rs",
    ROOT / "rust/src/trace_context.rs",
    ROOT / "examples/observability/json-ops-log.example.jsonl",
)

REQUIRED_ROUTES = ("/health", "/ready", "/status", "/metrics")

FORBIDDEN_TERMS = (
    "stripe",
    "billing",
    "pricing",
    "onboarding",
    "kovali",
    "hosted saas",
    "platform entitlements",
    "dashboard acl",
)

SECRET_PATTERNS = (
    re.compile(r"GOVAI_API_KEYS\s*=\s*['\"][^'\"]+['\"]"),
    re.compile(r"postgresql://[^\s\"']+"),
    re.compile(r"private-key-base64\s*=\s*['\"][a-zA-Z0-9+/=]{20,}"),
    re.compile(r"ED25519_PRIVATE_KEY_B64=[a-zA-Z0-9+/=]{20,}"),
)

SCAN_FILES = [
    ROOT / "docs/runtime-observability.md",
    ROOT / "docs/operator-diagnostics.md",
    ROOT / "docs/reports/runtime-observability-diagnostics.md",
    ROOT / "python/aigov_py/runtime_diagnostics.py",
    ROOT / "python/aigov_py/trace_context.py",
    ROOT / "examples/observability/json-ops-log.example.jsonl",
]


def main() -> int:
    errors: list[str] = []

    for path in REQUIRED_PATHS:
        if not path.exists():
            errors.append(f"missing: {path.relative_to(ROOT)}")

    router = ROUTER.read_text(encoding="utf-8")
    for route in REQUIRED_ROUTES:
        if f'"{route}"' not in router:
            errors.append(f"route {route} not mounted in govai_api.rs")

    if "runtime-diagnostics" not in (ROOT / "python/aigov_py/cli.py").read_text(encoding="utf-8"):
        errors.append("govai runtime-diagnostics not wired in cli.py")

    for path in SCAN_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        for term in FORBIDDEN_TERMS:
            if term in lower:
                errors.append(f"forbidden term {term!r} in {path.relative_to(ROOT)}")
        for pat in SECRET_PATTERNS:
            if pat.search(text):
                errors.append(f"possible secret in example/docs: {path.relative_to(ROOT)}")

    if errors:
        print("runtime-observability-check failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("runtime-observability-check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
