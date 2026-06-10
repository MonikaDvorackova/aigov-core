#!/usr/bin/env python3
"""Fail-closed validation for committed Cursor Marketplace listing media."""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from cursor_marketplace_publication import validate_publication_package


def main() -> int:
    errors: list[str] = []
    validate_publication_package(errors, require_listing_media=True)
    if errors:
        print("=== AIGov Cursor Marketplace listing media: FAIL ===")
        for msg in errors:
            print(f"  - {msg}")
        return 1
    print("=== AIGov Cursor Marketplace listing media: PASS ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
