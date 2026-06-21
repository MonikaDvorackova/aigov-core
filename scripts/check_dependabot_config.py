#!/usr/bin/env python3
"""Validate .github/dependabot.yml routes all update PRs to staging."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPENDABOT_YML = ROOT / ".github" / "dependabot.yml"
EXPECTED_TARGET_BRANCH = "staging"


def _load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PyYAML is required (pip install pyyaml)") from exc

    text = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must parse to a mapping at the root")
    return data


def _reject_corrupted_target_branch_lines(text: str) -> None:
    for lineno, line in enumerate(text.splitlines(), start=1):
        if "target-branch:" not in line:
            continue
        if re.search(r"target-branch:\s*\S+target-branch:", line):
            raise ValueError(
                f"{DEPENDABOT_YML}:{lineno}: duplicated target-branch key on one line"
            )
        stripped = line.lstrip()
        if stripped.startswith("target-branch:") and not line.startswith("    "):
            raise ValueError(
                f"{DEPENDABOT_YML}:{lineno}: target-branch must be indented under an updates entry"
            )


def validate_dependabot_config(path: Path = DEPENDABOT_YML) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"missing {path}")

    text = path.read_text(encoding="utf-8")
    _reject_corrupted_target_branch_lines(text)

    data = _load_yaml(path)
    updates = data.get("updates")
    if not isinstance(updates, list) or not updates:
        raise ValueError(f"{path} must define a non-empty updates list")

    ecosystems: list[str] = []
    for index, entry in enumerate(updates):
        if not isinstance(entry, dict):
            raise ValueError(f"updates[{index}] must be a mapping")
        ecosystem = entry.get("package-ecosystem")
        if not isinstance(ecosystem, str) or not ecosystem.strip():
            raise ValueError(f"updates[{index}] missing package-ecosystem")
        ecosystems.append(ecosystem.strip())
        target = entry.get("target-branch")
        if target != EXPECTED_TARGET_BRANCH:
            raise ValueError(
                f"updates[{index}] ({ecosystem}) target-branch must be {EXPECTED_TARGET_BRANCH!r}, got {target!r}"
            )

    return ecosystems


def main() -> int:
    try:
        ecosystems = validate_dependabot_config()
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"dependabot-config-check: FAIL — {exc}", file=sys.stderr)
        return 1

    joined = ", ".join(ecosystems)
    print(
        f"dependabot-config-check: OK — {len(ecosystems)} update block(s) target {EXPECTED_TARGET_BRANCH!r} ({joined})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
