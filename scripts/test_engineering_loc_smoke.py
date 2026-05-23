#!/usr/bin/env python3
"""Smoke test for engineering LOC documentation contract."""

from pathlib import Path
import sys

DOC = Path("docs/engineering-loc.md")

REQUIRED_TEXT = (
    "python3 scripts/test_engineering_loc_smoke.py",
)

def main() -> int:
    if not DOC.exists():
        print(f"Missing required documentation file: {DOC}", file=sys.stderr)
        return 1

    text = DOC.read_text(encoding="utf-8")

    missing = [item for item in REQUIRED_TEXT if item not in text]
    if missing:
        print("Engineering LOC smoke test failed:", file=sys.stderr)
        for item in missing:
            print(f"- missing text: {item}", file=sys.stderr)
        return 1

    print("Engineering LOC smoke test passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
