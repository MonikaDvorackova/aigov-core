#!/usr/bin/env python3
"""Aggregate release packaging readiness checks for GovAI Core."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from release_lib import (
    CHANGELOG_PATH,
    PYTHON_MANIFEST,
    RELEASE_MANIFEST,
    RUST_MANIFEST,
    ROOT,
    dumps_json,
    package_versions,
    read_text,
)

RELEASE_SCRIPTS = (
    "scripts/validate_changelog.py",
    "scripts/generate_release_notes.py",
    "scripts/release_readiness_report.py",
)

MAKEFILE_TARGETS = (
    "validate-changelog",
    "generate-release-notes",
    "release-readiness-report",
    "release-readiness-check",
)

RUST_METADATA_KEYS = (
    "license",
    "description",
    "repository",
    "readme",
    "keywords",
    "categories",
)
PYPROJECT_MARKERS = (
    'license = "Apache-2.0"',
    "authors =",
    "classifiers =",
    "[project.urls]",
)


def _load_validate_changelog():
    path = ROOT / "scripts" / "validate_changelog.py"
    spec = importlib.util.spec_from_file_location("validate_changelog", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _check_release_manifest(root: Path) -> list[str]:
    failures: list[str] = []
    manifest_path = root / "docs" / "releases" / "release-manifest.json"
    if not manifest_path.exists():
        return ["missing_release_manifest"]

    try:
        manifest = json.loads(read_text(manifest_path))
    except json.JSONDecodeError:
        return ["invalid_release_manifest_json"]

    stale_checks = {
        "release-manifest",
        "release-operations-check",
        "docs-links-strict",
    }
    for check in manifest.get("required_checks", []):
        if check in stale_checks:
            failures.append(f"stale_manifest_check:{check}")

    stale_scripts = (
        "scripts/validate_release_manifest.py",
        "scripts/release_operations_check.py",
    )
    for artifact in manifest.get("required_artifacts", []):
        path = artifact.get("path", "")
        if path in stale_scripts:
            failures.append(f"stale_manifest_artifact:{path}")

    required_checks = manifest.get("required_checks", [])
    for check in MAKEFILE_TARGETS:
        if check not in required_checks:
            failures.append(f"manifest_missing_check:{check}")

    return failures


def compute_release_readiness(root: Path = ROOT) -> tuple[dict[str, Any], int]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []

    for rel in RELEASE_SCRIPTS:
        ok = (root / rel).is_file()
        checks.append({"name": f"script_exists:{rel}", "ok": ok})
        if not ok:
            failures.append(f"missing_script:{rel}")

    makefile = read_text(root / "Makefile") if (root / "Makefile").exists() else ""
    for target in MAKEFILE_TARGETS:
        ok = f"{target}:" in makefile
        checks.append({"name": f"make_target:{target}", "ok": ok})
        if not ok:
            failures.append(f"missing_make_target:{target}")

    for path, label in (
        (RUST_MANIFEST, "rust_manifest"),
        (PYTHON_MANIFEST, "python_manifest"),
        (CHANGELOG_PATH, "changelog"),
        (RELEASE_MANIFEST, "release_manifest"),
        (root / "Dockerfile", "dockerfile"),
    ):
        ok = path.exists()
        checks.append({"name": f"path_exists:{label}", "ok": ok})
        if not ok:
            failures.append(f"missing_path:{path.relative_to(root)}")

    rust_text = read_text(RUST_MANIFEST) if RUST_MANIFEST.exists() else ""
    for key in RUST_METADATA_KEYS:
        ok = f"{key} =" in rust_text or f'{key} = "' in rust_text
        checks.append({"name": f"rust_metadata:{key}", "ok": ok})
        if not ok:
            failures.append(f"missing_rust_metadata:{key}")

    py_text = read_text(PYTHON_MANIFEST) if PYTHON_MANIFEST.exists() else ""
    for marker in PYPROJECT_MARKERS:
        ok = marker in py_text
        checks.append({"name": f"python_metadata:{marker}", "ok": ok})
        if not ok:
            failures.append(f"missing_python_metadata:{marker.split()[0]}")

    versions = package_versions(root)
    aligned = (
        versions.get("rust") is not None
        and versions.get("python") is not None
        and versions.get("rust") == versions.get("python")
    )
    checks.append({"name": "package_versions_aligned", "ok": aligned})
    if not aligned:
        failures.append("package_versions_not_aligned")

    validate_mod = _load_validate_changelog()
    changelog_payload, changelog_code = validate_mod.compute_changelog_validation(root)
    checks.append({"name": "validate_changelog", "ok": changelog_code == 0})
    if changelog_code != 0:
        failures.extend(changelog_payload.get("failures", []))

    manifest_failures = _check_release_manifest(root)
    checks.append({"name": "release_manifest_hygiene", "ok": not manifest_failures})
    failures.extend(manifest_failures)

    passed = sum(1 for check in checks if check["ok"])
    total = len(checks)
    score = round((passed / total) * 100) if total else 0

    payload = {
        "ok": not failures,
        "score": score,
        "checks_passed": passed,
        "checks_total": total,
        "package_versions": versions,
        "changelog": {
            "latest_released": changelog_payload.get("latest_released"),
            "has_unreleased": changelog_payload.get("has_unreleased"),
        },
        "checks": checks,
        "failures": failures,
    }
    return payload, 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON on stdout")
    args = parser.parse_args()

    payload, code = compute_release_readiness()
    if args.json:
        print(dumps_json(payload), end="")
    elif payload["ok"]:
        print(f"release_readiness_report: OK (score={payload['score']})")
    else:
        print("release_readiness_report failed:", file=sys.stderr)
        for failure in payload["failures"]:
            print(f"- {failure}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
