"""Shared helpers for GovAI Core release validation scripts (stdlib only)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
RUST_MANIFEST = ROOT / "rust" / "Cargo.toml"
PYTHON_MANIFEST = ROOT / "python" / "pyproject.toml"
RELEASE_MANIFEST = ROOT / "docs" / "releases" / "release-manifest.json"

VERSION_HEADER_RE = re.compile(
    r"^## \[(?P<version>[^\]]+)\](?:\s*-\s*(?P<date>\d{4}-\d{2}-\d{2}))?\s*$",
    re.MULTILINE,
)
TOML_VERSION_RE = re.compile(r'^version\s*=\s*"(?P<version>[^"]+)"', re.MULTILINE)
PYPROJECT_VERSION_RE = re.compile(
    r'^version\s*=\s*"(?P<version>[^"]+)"', re.MULTILINE
)


def dumps_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_toml_version(text: str) -> str | None:
    match = TOML_VERSION_RE.search(text)
    return match.group("version") if match else None


def parse_pyproject_version(text: str) -> str | None:
    match = PYPROJECT_VERSION_RE.search(text)
    return match.group("version") if match else None


def package_versions(root: Path = ROOT) -> dict[str, str | None]:
    rust_text = read_text(root / "rust" / "Cargo.toml") if (root / "rust" / "Cargo.toml").exists() else ""
    py_text = read_text(root / "python" / "pyproject.toml") if (root / "python" / "pyproject.toml").exists() else ""
    return {
        "rust": parse_toml_version(rust_text),
        "python": parse_pyproject_version(py_text),
    }


def parse_changelog_headers(text: str) -> list[dict[str, str | None]]:
    headers: list[dict[str, str | None]] = []
    for match in VERSION_HEADER_RE.finditer(text):
        headers.append(
            {
                "version": match.group("version"),
                "date": match.group("date"),
            }
        )
    return headers


def extract_changelog_section(text: str, version: str) -> str | None:
    pattern = re.compile(
        rf"^## \[{re.escape(version)}\](?:\s*-\s*\d{{4}}-\d{{2}}-\d{{2}})?\s*$",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return None
    start = match.end()
    next_header = re.search(r"^## \[", text[start:], re.MULTILINE)
    end = start + next_header.start() if next_header else len(text)
    return text[start:end].strip()


def parse_changelog_subsections(section: str) -> dict[str, list[str]]:
    current: str | None = None
    buckets: dict[str, list[str]] = {}
    for line in section.splitlines():
        if line.startswith("### "):
            current = line[4:].strip()
            buckets.setdefault(current, [])
            continue
        if current and line.startswith("- "):
            buckets[current].append(line[2:].strip())
    return buckets


def semver_tuple(version: str) -> tuple[int, ...]:
    core = version.split("-", 1)[0]
    parts: list[int] = []
    for piece in core.split("."):
        if not piece.isdigit():
            raise ValueError(f"invalid semver component: {piece!r}")
        parts.append(int(piece))
    return tuple(parts)
