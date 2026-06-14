#!/usr/bin/env python3
"""Generate Markdown release notes from a CHANGELOG version section."""

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
    extract_changelog_section,
    parse_changelog_subsections,
    read_text,
)

DEFAULT_SUBSECTIONS = ("Added", "Changed", "Fixed", "Security")


def render_release_notes(version: str, root: Path = ROOT) -> tuple[str, dict]:
    changelog_path = root / "CHANGELOG.md"
    text = read_text(changelog_path) if changelog_path.exists() else ""
    section = extract_changelog_section(text, version)
    warnings: list[str] = []

    if section is None:
        warnings.append(f"no_changelog_section:{version}")
        subsections = {name: [] for name in DEFAULT_SUBSECTIONS}
    else:
        subsections = parse_changelog_subsections(section)
        for name in DEFAULT_SUBSECTIONS:
            subsections.setdefault(name, [])

    highlights: list[str] = []
    if warnings:
        highlights.append(
            f"No `## [{version}]` section found in `CHANGELOG.md`; release notes are template-only."
        )
        highlights.append("Update CHANGELOG.md before publishing this version.")
    else:
        for name in DEFAULT_SUBSECTIONS:
            for item in subsections.get(name, []):
                highlights.append(item)
        if not highlights:
            highlights.append("See CHANGELOG.md for detailed entries.")

    lines = [
        f"# GovAI {version} — release notes",
        "",
        "## Highlights",
        "",
    ]
    for item in highlights:
        lines.append(f"- {item}")
    lines.append("")

    for name in DEFAULT_SUBSECTIONS:
        lines.extend([f"## {name}", ""])
        items = subsections.get(name, [])
        if items:
            for item in items:
                lines.append(f"- {item}")
        else:
            lines.append("- *(none documented)*")
        lines.append("")

    lines.extend(
        [
            "## Compatibility notes",
            "",
            "- See [compatibility-policy.md](docs/releases/compatibility-policy.md) and "
            "[versioning-policy.md](docs/releases/versioning-policy.md) for semver intent.",
            "## Upgrade instructions",
            "",
            "- Run `make release-readiness-check` on the release candidate commit.",
            "- Review [release-checklist.md](docs/releases/release-checklist.md) and "
            "[release-runbook.md](docs/releases/release-runbook.md).",
            "",
        ]
    )

    meta = {
        "ok": True,
        "version": version,
        "changelog_path": str(changelog_path.relative_to(root)),
        "warnings": warnings,
        "subsections": {name: subsections.get(name, []) for name in DEFAULT_SUBSECTIONS},
    }
    return "\n".join(lines), meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Release version (for example 0.2.1)")
    parser.add_argument("--out", type=Path, help="Write Markdown to this path")
    parser.add_argument("--json", action="store_true", help="Emit metadata JSON instead of notes")
    args = parser.parse_args()

    notes, meta = render_release_notes(args.version)
    if args.json:
        print(dumps_json(meta), end="")
        return 0

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(notes, encoding="utf-8")
        print(f"Wrote release notes: {args.out}")
    else:
        sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
