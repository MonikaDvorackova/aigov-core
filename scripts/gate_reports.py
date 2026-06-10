#!/usr/bin/env python3
"""Validate required audit report headings."""

from pathlib import Path
import sys

REQUIRED_HEADINGS = (
    "## Evaluation gate",
    "## Human approval gate",
)

REPORT_DIR = Path("docs/reports")


def main() -> int:
    if not REPORT_DIR.exists():
        print("Report gate failed: docs/reports does not exist", file=sys.stderr)
        return 1

    failures: list[str] = []

    for report in sorted(REPORT_DIR.glob("*.md")):
        text = report.read_text(encoding="utf-8")
        for heading in REQUIRED_HEADINGS:
            if heading not in text:
                failures.append(f"{report}: missing required heading {heading!r}")

    if failures:
        print("Report gate failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("Report gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
