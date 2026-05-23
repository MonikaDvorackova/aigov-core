#!/usr/bin/env python3
"""Validate GovAI public SDK package claims."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


AUDIT_REPORT = "docs/reports/hosted-runtime-residue-cleanup.md"

REQUIRED_PATHS = (
    "README.md",
    "Makefile",
    "python/pyproject.toml",
    "python/aigov_py/cli.py",
    AUDIT_REPORT,
)

CLAIM_SCAN_PATHS = (
    "README.md",
    "docs/project/contributor_quickstart.md",
    "docs/project/contributor_workflow.md",
    "dashboard/lib/landing/landingPageContent.ts",
    "dashboard/lib/landing/govaiWorkflowStages.ts",
)

FORBIDDEN_RUST_SDK_PATTERNS = (
    "Rust SDK",
    "rust sdk",
    "Rust client SDK",
)


def dumps_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _is_public_functions_sdk_package(text: str) -> bool:
    try:
        package = json.loads(text)
    except json.JSONDecodeError:
        return False

    return (
        package.get("name") == "@govai/functions-sdk"
        and isinstance(package.get("version"), str)
        and package.get("publishConfig", {}).get("access") == "public"
        and "files" in package
    )


def _read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def compute_public_sdk_packages(root: Path) -> tuple[dict, int]:
    failures: list[str] = []

    for rel in REQUIRED_PATHS:
        if not (root / rel).exists():
            failures.append(f"missing_required_path:{rel}")

    makefile = _read(root, "Makefile")
    for target in (
        "public-sdk-packages-check",
        "sdk-ecosystem-check",
        "typescript-client-check",
    ):
        if target not in makefile:
            failures.append(f"missing_make_target:{target}")

    package_path = root / "typescript-sdk/package.json"
    package_text = _read(root, "typescript-sdk/package.json")
    if package_path.exists() and not _is_public_functions_sdk_package(package_text):
        failures.append("invalid_public_functions_sdk_package")

    combined_claim_text = "\n".join(_read(root, rel) for rel in CLAIM_SCAN_PATHS)
    for pattern in FORBIDDEN_RUST_SDK_PATTERNS:
        if pattern in combined_claim_text:
            failures.append("rust_sdk_label")
            break

    client_path = root / "typescript-sdk/src/client.ts"
    if client_path.exists():
        client_text = _read(root, "typescript-sdk/src/client.ts")
        if "GovAIClient" not in client_text:
            failures.append("missing_govai_client_export")
        if "exportAudit" not in client_text:
            failures.append("missing_export_audit")
    else:
        pyproject_text = _read(root, "python/pyproject.toml")
        cli_text = _read(root, "python/aigov_py/cli.py")
        if "aigov-py" not in pyproject_text and "govai" not in pyproject_text:
            failures.append("missing_python_sdk_package_metadata")
        if "verify-evidence-pack" not in cli_text:
            failures.append("missing_python_sdk_cli_contract")

    audit_text = _read(root, AUDIT_REPORT)
    if "## Evaluation gate" not in audit_text:
        failures.append("missing_evaluation_gate")
    if "## Human approval gate" not in audit_text:
        failures.append("missing_human_approval_gate")

    failures = sorted(set(failures))
    ok = not failures

    payload = {
        "ok": ok,
        "score": 100 if ok else 0,
        "failures": failures,
        "checks": {
            "required_paths": list(REQUIRED_PATHS),
            "claim_scan_paths": list(CLAIM_SCAN_PATHS),
            "audit_report": AUDIT_REPORT,
        },
    }

    return payload, 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    payload, code = compute_public_sdk_packages(args.root.resolve())

    if args.json:
        print(dumps_json(payload))
    elif code == 0:
        print("public SDK packages check passed.")
    else:
        print("public SDK packages check failed:", file=sys.stderr)
        for failure in payload["failures"]:
            print(f"- {failure}", file=sys.stderr)

    return code


if __name__ == "__main__":
    raise SystemExit(main())
