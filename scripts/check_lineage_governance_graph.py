#!/usr/bin/env python3
"""Validate multi-agent lineage governance graph foundation."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = (
    ROOT / "rust/src/governance_graph.rs",
    ROOT / "rust/src/lineage_projection.rs",
    ROOT / "rust/src/lineage_validation.rs",
    ROOT / "rust/src/bin/lineage_graph_once.rs",
    ROOT / "python/aigov_py/lineage_graph.py",
    ROOT / "docs/multi-agent-lineage.md",
    ROOT / "docs/reports/multi-agent-lineage-governance-graph.md",
)

REQUIRED_SNIPPETS = (
    (ROOT / "rust/src/schema.rs", "parent_run_id"),
    (ROOT / "rust/src/schema.rs", "root_run_id"),
    (ROOT / "rust/src/governance_graph.rs", "agent_delegated"),
    (ROOT / "rust/src/audit_export.rs", '"lineage"'),
    (ROOT / "rust/src/replay_validation.rs", "validate_lineage_for_run"),
    (ROOT / "python/aigov_py/cli.py", "lineage-graph"),
    (ROOT / "rust/Cargo.toml", "lineage_graph_once"),
)

FORBIDDEN_TERMS = (
    "stripe",
    "billing",
    "pricing",
    "onboarding",
    "kovali",
    "hosted saas",
    "platform entitlements",
    "dashboard acl",
    "fake guarantee",
    "100% secure",
)

FAKE_GUARANTEE_PATTERNS = (
    re.compile(r"\bha guarantee\b", re.I),
    re.compile(r"\bguaranteed ha\b", re.I),
    re.compile(r"\bmulti-tenant cryptographic isolation\b", re.I),
)

SCAN_FILES = [
    ROOT / "docs/multi-agent-lineage.md",
    ROOT / "docs/reports/multi-agent-lineage-governance-graph.md",
    ROOT / "docs/threat-model.md",
    ROOT / "python/aigov_py/lineage_graph.py",
]


def main() -> int:
    errors: list[str] = []

    for path in REQUIRED_PATHS:
        if not path.exists():
            errors.append(f"missing: {path.relative_to(ROOT)}")

    for path, needle in REQUIRED_SNIPPETS:
        if not path.exists():
            errors.append(f"missing file for snippet check: {path.relative_to(ROOT)}")
            continue
        if needle not in path.read_text(encoding="utf-8"):
            errors.append(f"missing {needle!r} in {path.relative_to(ROOT)}")

    # replay schema unchanged
    replay_validation = (ROOT / "rust/src/replay_validation.rs").read_text(encoding="utf-8")
    if "EXPORT_SCHEMA_V1" not in replay_validation:
        errors.append("replay EXPORT_SCHEMA_V1 constant missing")

    for path in SCAN_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        for term in FORBIDDEN_TERMS:
            if term in lower:
                errors.append(f"forbidden term {term!r} in {path.relative_to(ROOT)}")
        for pat in FAKE_GUARANTEE_PATTERNS:
            if pat.search(text):
                errors.append(f"fake guarantee language in {path.relative_to(ROOT)}")

    threat = ROOT / "docs/threat-model.md"
    if threat.exists():
        body = threat.read_text(encoding="utf-8").lower()
        if "lineage and delegation" not in body or "forged delegation" not in body:
            errors.append("threat-model.md missing lineage extension")

    if errors:
        print("lineage-governance-check failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("lineage-governance-check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
