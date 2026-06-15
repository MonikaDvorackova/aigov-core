#!/usr/bin/env python3
"""Validate CHANGELOG.md structure and version alignment with package manifests."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from release_lib import (
    CHANGELOG_PATH,
    ROOT,
    dumps_json,
    package_versions,
    parse_changelog_headers,
    read_text,
    semver_tuple,
)


def compute_changelog_validation(root=ROOT) -> tuple[dict, int]:
    failures: list[str] = []
    changelog_path = root / "CHANGELOG.md"

    if not changelog_path.exists():
        failures.append("missing_changelog")
        payload = {
            "ok": False,
            "changelog_path": str(changelog_path.relative_to(root)),
            "failures": failures,
        }
        return payload, 1

    text = read_text(changelog_path)
    if not text.lstrip().startswith("# Changelog"):
        failures.append("missing_changelog_title")

    headers = parse_changelog_headers(text)
    versions = package_versions(root)
    rust_version = versions.get("rust")
    python_version = versions.get("python")

    has_unreleased = any(h["version"] == "Unreleased" for h in headers)
    if not has_unreleased:
        failures.append("missing_unreleased_section")

    released = [h for h in headers if h["version"] != "Unreleased"]
    latest_released = released[0]["version"] if released else None
    latest_released_date = released[0]["date"] if released else None

    if not released:
        failures.append("missing_released_section")
    elif latest_released_date is None:
        failures.append(f"missing_release_date:{latest_released}")

    if rust_version and python_version and rust_version != python_version:
        failures.append(
            f"package_version_mismatch:rust={rust_version},python={python_version}"
        )

    if rust_version and latest_released:
        try:
            if semver_tuple(rust_version) != semver_tuple(latest_released):
                failures.append(
                    f"changelog_latest_mismatch:packages={rust_version},changelog={latest_released}"
                )
        except ValueError:
            failures.append("invalid_semver_in_manifest_or_changelog")

    payload = {
        "ok": not failures,
        "changelog_path": str(changelog_path.relative_to(root)),
        "package_versions": versions,
        "latest_released": latest_released,
        "latest_released_date": latest_released_date,
        "has_unreleased": has_unreleased,
        "failures": failures,
    }
    return payload, 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON on stdout")
    args = parser.parse_args()

    payload, code = compute_changelog_validation()
    if args.json:
        print(dumps_json(payload), end="")
    elif payload["ok"]:
        print("validate_changelog: OK")
    else:
        print("validate_changelog failed:", file=sys.stderr)
        for failure in payload["failures"]:
            print(f"- {failure}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
