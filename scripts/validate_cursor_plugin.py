#!/usr/bin/env python3
"""Validate AIGov Cursor plugin layout, marketplace manifest, and bundled assets.

Exit code 0 on success, non-zero on failure.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from cursor_marketplace_publication import validate_publication_package

REPO_ROOT = _SCRIPTS_DIR.parent
PLUGIN_DIR = REPO_ROOT / ".cursor-plugin"
MANIFEST = PLUGIN_DIR / "plugin.json"
RULES_DIR = REPO_ROOT / "rules"
SKILLS_DIR = REPO_ROOT / "skills"
REPO_MCP_JSON = REPO_ROOT / "mcp.json"
LOGO_PATH = PLUGIN_DIR / "assets" / "logo.png"
MCP_SERVER = REPO_ROOT / "mcp" / "aigov_mcp_server.py"
README = PLUGIN_DIR / "README.md"
LOCAL_CONFIG = PLUGIN_DIR / "examples" / "local-config.json"

NAME_KEBAB_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
FORBIDDEN_MARKERS = (
    (re.compile(r"\bTODO\b", re.IGNORECASE), "TODO"),
    (re.compile(r"\bFIXME\b", re.IGNORECASE), "FIXME"),
    (re.compile(r"\bPLACEHOLDER\b", re.IGNORECASE), "PLACEHOLDER"),
)

def _fail(msgs: list[str]) -> int:
    print("=== AIGov Cursor plugin validation: FAIL ===")
    for m in msgs:
        print(f"  - {m}")
    return 1


def _ok(msg: str) -> None:
    print(f"  OK: {msg}")


def _scan_forbidden(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for rx, name in FORBIDDEN_MARKERS:
        if rx.search(text):
            errors.append(f"{path.relative_to(REPO_ROOT)}: contains forbidden marker {name!r}")


def _parse_yaml_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """Parse a leading --- ... --- block into key/value strings (single-line values)."""
    raw = raw.lstrip("\ufeff")
    if not raw.startswith("---"):
        return {}, raw
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw
    meta: dict[str, str] = {}
    end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
        line = lines[i]
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        val = rest.strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        meta[key] = val
    if end < 0:
        return {}, raw
    body = "\n".join(lines[end + 1 :])
    return meta, body


def _validate_mcp_servers_block(obj: Any, label: str, errors: list[str]) -> None:
    if not isinstance(obj, dict) or not obj:
        errors.append(f"{label}: must be a non-empty object")
        return
    for srv_name, cfg in obj.items():
        if not isinstance(srv_name, str) or not srv_name.strip():
            errors.append(f"{label}: invalid server key")
            continue
        if not isinstance(cfg, dict):
            errors.append(f"{label}: server {srv_name!r} must be an object")
            continue
        cmd = cfg.get("command")
        args = cfg.get("args")
        if not isinstance(cmd, str) or not cmd.strip():
            errors.append(f"{label}: {srv_name!r} missing command")
        if not isinstance(args, list) or not args:
            errors.append(f"{label}: {srv_name!r} missing args array")
        else:
            if not all(isinstance(a, str) for a in args):
                errors.append(f"{label}: {srv_name!r} args must be strings")
            elif args and not str(args[0]).endswith(".py"):
                errors.append(f"{label}: {srv_name!r} args[0] should be the MCP server script path")


def _manifest_mcp_or_file(data: dict[str, Any], errors: list[str]) -> None:
    has_inline = isinstance(data.get("mcpServers"), dict) and data["mcpServers"]
    has_file = REPO_MCP_JSON.is_file()
    if has_inline:
        _validate_mcp_servers_block(data.get("mcpServers"), "plugin.json mcpServers", errors)
    if has_file:
        try:
            mcp_data = json.loads(REPO_MCP_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"mcp.json is not valid JSON: {e}")
            return
        ms = mcp_data.get("mcpServers")
        if isinstance(ms, dict) and ms:
            _validate_mcp_servers_block(ms, "mcp.json mcpServers", errors)
        else:
            errors.append("mcp.json: missing or empty mcpServers")
    if not has_inline and not has_file:
        errors.append("Provide mcpServers in plugin.json and/or mcp.json at repository root")


def _validate_open_plugins_layout(errors: list[str]) -> None:
    if not RULES_DIR.is_dir():
        errors.append("Open Plugins layout: rules/ missing at repository root")
    elif not list(RULES_DIR.glob("*.mdc")):
        errors.append("Open Plugins layout: rules/ has no .mdc files at repository root")
    if not SKILLS_DIR.is_dir():
        errors.append("Open Plugins layout: skills/ missing at repository root")
    elif not any(
        (child / "SKILL.md").is_file()
        for child in SKILLS_DIR.iterdir()
        if child.is_dir() and not child.name.startswith(".")
    ):
        errors.append("Open Plugins layout: skills/*/SKILL.md missing at repository root")
    if not REPO_MCP_JSON.is_file():
        errors.append("Open Plugins layout: mcp.json missing at repository root")
    if not LOGO_PATH.is_file():
        errors.append("Open Plugins layout: .cursor-plugin/assets/logo.png missing")


def _validate_manifest(data: dict[str, Any], errors: list[str]) -> None:
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("plugin.json: name must be a non-empty string")
    elif not NAME_KEBAB_RE.match(name.strip()):
        errors.append(
            "plugin.json: name must be lowercase kebab-case "
            "(^[a-z][a-z0-9]*(-[a-z0-9]+)*$), e.g. govai"
        )

    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        errors.append("plugin.json: version must be a non-empty string")

    for key in ("author", "homepage", "repository", "license", "description"):
        v = data.get(key)
        if not isinstance(v, str) or not v.strip():
            errors.append(f"plugin.json: {key!r} must be a non-empty string")

    kw = data.get("keywords")
    if not isinstance(kw, list) or not kw:
        errors.append("plugin.json: keywords must be a non-empty array of strings")
    elif not all(isinstance(x, str) and x.strip() for x in kw):
        errors.append("plugin.json: keywords must contain only non-empty strings")

    logo = data.get("logo")
    if not isinstance(logo, str) or not logo.strip():
        errors.append("plugin.json: logo must be a non-empty path string")
    elif not LOGO_PATH.is_file():
        errors.append("plugin.json: logo file missing: .cursor-plugin/assets/logo.png")

    rules_ref = data.get("rules")
    if not isinstance(rules_ref, str) or rules_ref.strip() != "rules":
        errors.append('plugin.json: rules must be "rules" (repository-root rules/)')
    elif not RULES_DIR.is_dir():
        errors.append("plugin.json: rules directory missing at repository root")
    elif not list(RULES_DIR.glob("*.mdc")):
        errors.append("plugin.json: rules/ has no .mdc files at repository root")

    skills_ref = data.get("skills")
    if not isinstance(skills_ref, str) or skills_ref.strip() != "skills":
        errors.append('plugin.json: skills must be "skills" (repository-root skills/)')
    elif not SKILLS_DIR.is_dir():
        errors.append("plugin.json: skills directory missing at repository root")

    _manifest_mcp_or_file(data, errors)
    _validate_open_plugins_layout(errors)


def _validate_skill_tree(skills_dir: Path, errors: list[str]) -> list[Path]:
    skill_files: list[Path] = []
    if not skills_dir.is_dir():
        return skill_files
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"skill folder missing SKILL.md: {child.relative_to(REPO_ROOT)}")
            continue
        raw = skill_md.read_text(encoding="utf-8")
        meta, _body = _parse_yaml_frontmatter(raw)
        if not meta.get("name") or not str(meta["name"]).strip():
            errors.append(f"{skill_md.relative_to(REPO_ROOT)}: frontmatter missing name")
        if not meta.get("description") or not str(meta["description"]).strip():
            errors.append(f"{skill_md.relative_to(REPO_ROOT)}: frontmatter missing description")
        skill_files.append(skill_md)
    if not skill_files:
        errors.append("skills/: no skill subdirectories with SKILL.md found")
    return skill_files


def _check_nonempty_text(path: Path, label: str, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"missing {label}: {path.relative_to(REPO_ROOT)}")
        return
    raw = path.read_bytes()
    if not raw.strip():
        errors.append(f"empty file ({label}): {path.relative_to(REPO_ROOT)}")


def main() -> int:
    errors: list[str] = []

    if not MANIFEST.is_file():
        return _fail([".cursor-plugin/plugin.json does not exist"])

    try:
        data: dict[str, Any] = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return _fail([f"plugin.json is not valid JSON: {e}"])

    _validate_manifest(data, errors)

    if not MCP_SERVER.is_file():
        errors.append("mcp/aigov_mcp_server.py missing")
    _check_nonempty_text(README, "README", errors)
    _check_nonempty_text(LOCAL_CONFIG, "local MCP example config", errors)

    rule_paths = sorted(RULES_DIR.glob("*.mdc")) if RULES_DIR.is_dir() else []
    for p in rule_paths:
        _check_nonempty_text(p, "rule", errors)
        if p.is_file():
            _scan_forbidden(p, errors)

    if SKILLS_DIR.is_dir():
        for legacy in sorted(SKILLS_DIR.glob("*.md")):
            errors.append(
                f"legacy flat skill file not allowed (use skills/<name>/SKILL.md): "
                f"{legacy.relative_to(REPO_ROOT)}"
            )

    skill_paths = _validate_skill_tree(SKILLS_DIR, errors)
    for p in skill_paths:
        _check_nonempty_text(p, "skill", errors)
        if p.is_file():
            _scan_forbidden(p, errors)

    _check_nonempty_text(REPO_MCP_JSON, "repository-root mcp.json", errors)
    if REPO_MCP_JSON.is_file():
        try:
            json.loads(REPO_MCP_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"mcp.json invalid JSON: {e}")

    if LOCAL_CONFIG.is_file():
        try:
            json.loads(LOCAL_CONFIG.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"invalid JSON: {LOCAL_CONFIG.relative_to(REPO_ROOT)}: {e}")

    validate_publication_package(errors, require_listing_media=False)

    for rel in (
        "dashboard/brand/govai-wordmark.png",
        "dashboard/public/govai-wordmark.png",
        "dashboard/scripts/copy-approved-wordmark.sh",
    ):
        path = REPO_ROOT / rel
        if path.is_file():
            errors.append(f"unapproved logo artifact must not be present: {rel}")

    if errors:
        return _fail(errors)

    print("=== AIGov Cursor plugin validation: PASS ===")
    _ok("plugin.json marketplace fields (name, version, author, homepage, repository, license, keywords, logo)")
    _ok('plugin.json rules="rules" and skills="skills" at repository root')
    _ok("plugin.json mcpServers and/or repository-root mcp.json")
    _ok("Open Plugins layout (rules/, skills/, mcp.json, logo at expected paths)")
    _ok(f"rules ({len(rule_paths)} files)")
    _ok(f"skills ({len(skill_paths)} SKILL.md files under skills/*/)")
    _ok("mcp/aigov_mcp_server.py present")
    _ok(".cursor-plugin/README.md present and non-empty")
    _ok(".cursor-plugin/examples/local-config.json present and non-empty")
    _ok("no TODO/FIXME/PLACEHOLDER markers in rules or skills")
    _ok("marketplace logo and hero derived from dashboard/brand/aigov-mark.ico")
    _ok("publication package structure and marketplace-assets.json")
    _ok("publication status explicitly not live in Cursor Marketplace")
    _ok("checklist evidence matches completed pre-submit items")
    _ok("installation model documents full-repository MCP requirement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
