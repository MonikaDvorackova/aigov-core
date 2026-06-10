#!/usr/bin/env python3
"""Shared validation logic for AIGov Cursor Marketplace publication package."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO_ROOT / ".cursor-plugin"
BRAND_ICO = REPO_ROOT / "dashboard" / "brand" / "aigov-mark.ico"
BRAND_DERIVATION = PLUGIN_DIR / "assets" / "brand-derivation.json"
PUBLICATION_DIR = PLUGIN_DIR / "publication"
ASSETS_MANIFEST = PLUGIN_DIR / "assets" / "marketplace-assets.json"
INSTALLATION_MODEL = PLUGIN_DIR / "installation-model.json"
CHECKLIST_STATE = PUBLICATION_DIR / "checklist-state.json"
CHECKLIST_EVIDENCE = PUBLICATION_DIR / "checklist-evidence.json"

ASSET_STATUSES = frozenset({"committed", "missing", "missing_unapproved_asset", "not_required"})
LISTING_BLOCK_STATUSES = frozenset({"missing", "missing_unapproved_asset"})

FORBIDDEN_ASSET_PATH_SEGMENTS = (
    "generated-previews",
    "submission-placeholders",
)

FORBIDDEN_REPO_FILES = (
    "scripts/generate_cursor_marketplace_placeholders.py",
    "scripts/generate_cursor_marketplace_hero.py",
    "scripts/render_cursor_marketplace_capture_views.py",
)

PUBLICATION_REQUIRED_FILES = (
    "README.md",
    "status.md",
    "submission-copy.md",
    "demo-flow.md",
    "screenshot-plan.md",
    "release-checklist.md",
    "reviewer-notes.md",
    "support-and-contact.md",
    "cursor-version-policy.md",
    "installation-model.md",
    "manual-capture-procedure.md",
    "pre-submit-checklist.md",
)

STATUS_REQUIRED_PHRASES = (
    "Internally usable",
    "Not live",
    "aigov-mark.ico",
)

FALSE_LIVE_CLAIMS = (
    re.compile(r"\bnow live in cursor marketplace\b", re.IGNORECASE),
    re.compile(r"\blisting approved\b", re.IGNORECASE),
    re.compile(r"\balready published\b", re.IGNORECASE),
)

CHECKBOX_ID_RE = re.compile(r"<!--\s*id:([a-z0-9-]+)\s*-->")


def _git_tracks(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    proc = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_approved_brand_source(errors: list[str]) -> None:
    if not BRAND_ICO.is_file():
        errors.append("approved brand source missing: dashboard/brand/aigov-mark.ico")
        return

    if not BRAND_DERIVATION.is_file():
        errors.append("missing .cursor-plugin/assets/brand-derivation.json")
        return

    try:
        data = _read_json(BRAND_DERIVATION)
    except json.JSONDecodeError:
        errors.append("brand-derivation.json invalid JSON")
        return

    if data.get("approved_source") != "dashboard/brand/aigov-mark.ico":
        errors.append("brand-derivation.json approved_source must be dashboard/brand/aigov-mark.ico")
    if data.get("derivation") != "lossless_composite_no_scale":
        errors.append("brand-derivation.json derivation must be lossless_composite_no_scale")

    expected_source = data.get("approved_source_sha256")
    if not isinstance(expected_source, str) or _sha256(BRAND_ICO) != expected_source:
        errors.append("brand-derivation.json approved_source_sha256 does not match aigov-mark.ico")

    outputs = data.get("outputs")
    if not isinstance(outputs, dict):
        errors.append("brand-derivation.json outputs must be an object")
        return

    for rel, meta in outputs.items():
        if not isinstance(meta, dict):
            errors.append(f"brand-derivation.json outputs[{rel!r}] must be an object")
            continue
        expected_hash = meta.get("sha256")
        path = PLUGIN_DIR / rel
        if not path.is_file():
            errors.append(f"derived brand output missing on disk: .cursor-plugin/{rel}")
            continue
        if not isinstance(expected_hash, str) or _sha256(path) != expected_hash:
            errors.append(f"brand-derivation.json sha256 mismatch for .cursor-plugin/{rel}")


def _resolve_path(rel: str) -> Path:
    if rel.startswith(".cursor-plugin/"):
        return REPO_ROOT / rel
    if rel.startswith("mcp/") or rel.startswith("scripts/") or rel.startswith("docs/"):
        return REPO_ROOT / rel
    return PLUGIN_DIR / rel


def _evidence_ok(spec: dict[str, Any]) -> bool:
    kind = spec.get("type")
    if kind == "file_exists":
        return _resolve_path(str(spec["path"])).is_file()
    if kind == "file_contains":
        path = _resolve_path(str(spec["path"]))
        if not path.is_file():
            return False
        text = path.read_text(encoding="utf-8")
        return all(needle in text for needle in spec.get("needles", []))
    if kind == "json_field":
        path = _resolve_path(str(spec["path"]))
        if not path.is_file():
            return False
        data = _read_json(path)
        value = data
        for key in str(spec["field"]).split("."):
            if not isinstance(value, dict):
                return False
            value = value.get(key)
        return value == spec.get("equals")
    if kind == "json_nonempty_list":
        path = _resolve_path(str(spec["path"]))
        if not path.is_file():
            return False
        data = _read_json(path)
        value = data.get(spec["field"]) if isinstance(data, dict) else None
        return isinstance(value, list) and len(value) > 0
    if kind == "installation_model":
        path = INSTALLATION_MODEL
        if not path.is_file():
            return False
        data = _read_json(path)
        return data.get("cursor_marketplace_submission_model") == spec.get("expected_model")
    if kind == "manifest_missing_assets":
        if not ASSETS_MANIFEST.is_file():
            return False
        data = _read_json(ASSETS_MANIFEST)
        assets = data.get("assets", [])
        if not isinstance(assets, list):
            return False
        missing = [
            a
            for a in assets
            if isinstance(a, dict) and a.get("status") in LISTING_BLOCK_STATUSES
        ]
        return len(missing) >= int(spec.get("min_count", 1))
    if kind == "file_missing":
        path = _resolve_path(str(spec["path"]))
        return not path.is_file()
    return False


def _parse_checkbox_ids(md_path: Path) -> dict[str, bool]:
    checked: dict[str, bool] = {}
    if not md_path.is_file():
        return checked
    for line in md_path.read_text(encoding="utf-8").splitlines():
        m = CHECKBOX_ID_RE.search(line)
        if not m:
            continue
        item_id = m.group(1)
        checked[item_id] = line.strip().startswith("- [x]")
    return checked


def _scan_forbidden_placeholder_artifacts(errors: list[str]) -> None:
    for rel in FORBIDDEN_REPO_FILES:
        if (REPO_ROOT / rel).is_file():
            errors.append(f"placeholder generator must not be present: {rel}")

    assets_root = PLUGIN_DIR / "assets"
    if not assets_root.is_dir():
        return
    manifest = _read_json(ASSETS_MANIFEST) if ASSETS_MANIFEST.is_file() else {"assets": []}
    by_path = {
        a.get("path"): a
        for a in manifest.get("assets", [])
        if isinstance(a, dict) and isinstance(a.get("path"), str)
    }
    for path in assets_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(PLUGIN_DIR).as_posix()
        if any(seg in rel for seg in FORBIDDEN_ASSET_PATH_SEGMENTS):
            errors.append(f"forbidden placeholder asset path present: .cursor-plugin/{rel}")
        if "capture-evidence/views/" in rel and path.suffix.lower() == ".html":
            errors.append(f"mock capture view must not be shipped: .cursor-plugin/{rel}")
        if rel == "assets/logo.png" and path.is_file():
            entry = by_path.get(rel)
            if entry is None or entry.get("status") != "committed":
                errors.append(
                    "unapproved or undocumented plugin logo present on disk: .cursor-plugin/assets/logo.png"
                )
        if "listing/" in rel and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm"}:
            entry = by_path.get(rel)
            if entry is None or entry.get("status") != "committed":
                errors.append(
                    f"listing media on disk without committed manifest status: .cursor-plugin/{rel}"
                )

    for rel in (
        "dashboard/brand/govai-wordmark.png",
        "dashboard/public/govai-wordmark.png",
        "dashboard/scripts/copy-approved-wordmark.sh",
    ):
        if (REPO_ROOT / rel).is_file():
            errors.append(f"unapproved logo artifact must not be present: {rel}")


def validate_publication_package(errors: list[str], *, require_listing_media: bool = True) -> None:
    for name in PUBLICATION_REQUIRED_FILES:
        path = PUBLICATION_DIR / name
        if not path.is_file() or not path.read_bytes().strip():
            errors.append(f"missing or empty publication/{name}")

    status = PUBLICATION_DIR / "status.md"
    if status.is_file():
        text = status.read_text(encoding="utf-8")
        for phrase in STATUS_REQUIRED_PHRASES:
            if phrase not in text:
                errors.append(f"publication/status.md must include phrase: {phrase!r}")
        for rx in FALSE_LIVE_CLAIMS:
            if rx.search(text):
                errors.append(f"publication/status.md contains false live claim: {rx.pattern}")

    for rel in (
        ".cursor-plugin/README.md",
        ".cursor-plugin/marketplace.md",
        ".cursor-plugin/publication/submission-copy.md",
    ):
        path = REPO_ROOT / rel
        if not path.is_file():
            errors.append(f"missing marketplace doc: {rel}")
            continue
        for rx in FALSE_LIVE_CLAIMS:
            if rx.search(path.read_text(encoding="utf-8")):
                errors.append(f"{rel} contains false live claim: {rx.pattern}")

    if not INSTALLATION_MODEL.is_file():
        errors.append("missing .cursor-plugin/installation-model.json")
    else:
        model = _read_json(INSTALLATION_MODEL)
        full = model.get("scopes", {}).get("full_repository", {})
        if not full.get("mcp_tools_available"):
            errors.append("installation-model.json must mark full_repository.mcp_tools_available true")
        if not full.get("recommended_for_listing"):
            errors.append("installation-model.json must recommend full_repository for listing")

    if not ASSETS_MANIFEST.is_file():
        errors.append("missing .cursor-plugin/assets/marketplace-assets.json")
        return

    manifest = _read_json(ASSETS_MANIFEST)
    if manifest.get("publication_state") != "pre_submit_not_live":
        errors.append("marketplace-assets.json publication_state must be pre_submit_not_live")

    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        errors.append("marketplace-assets.json assets must be a non-empty array")
        return

    committed = 0
    missing = 0
    for entry in assets:
        if not isinstance(entry, dict):
            errors.append("marketplace-assets.json: each asset must be an object")
            continue
        asset_id = entry.get("id", "<unknown>")
        status = entry.get("status")
        rel = entry.get("path")
        if status not in ASSET_STATUSES:
            errors.append(f"marketplace-assets.json asset {asset_id!r}: invalid status {status!r}")
            continue
        if not isinstance(rel, str) or not rel.strip():
            errors.append(f"marketplace-assets.json asset {asset_id!r}: missing path")
            continue
        path = PLUGIN_DIR / rel.strip()
        if status == "committed":
            committed += 1
            if not path.is_file():
                errors.append(f"committed marketplace asset missing on disk: {path.relative_to(REPO_ROOT)}")
        elif status in LISTING_BLOCK_STATUSES:
            missing += 1
            if require_listing_media:
                if status == "missing_unapproved_asset":
                    errors.append(
                        f"listing asset missing user-approved file (blocks portal submit): {asset_id!r}"
                    )
                else:
                    errors.append(f"listing asset missing (documented, blocks portal submit): {asset_id!r}")
            if path.is_file():
                errors.append(
                    f"blocked listing asset must not exist on disk: {path.relative_to(REPO_ROOT)}"
                )
            if _git_tracks(path):
                errors.append(
                    f"blocked listing asset must not be git-tracked: {path.relative_to(REPO_ROOT)}"
                )
        elif status == "not_required" and path.is_file() and _git_tracks(path):
            errors.append(f"not_required asset should not be committed: {path.relative_to(REPO_ROOT)}")

    if committed < 1:
        errors.append("marketplace-assets.json must list at least one committed asset")
    if not any(
        isinstance(a, dict) and a.get("id") == "demo_flow_evidence" and a.get("status") == "committed"
        for a in assets
    ):
        errors.append("marketplace-assets.json must keep demo_flow_evidence committed")

    for rel_path in (
        "assets/capture-evidence/README.md",
        "assets/listing/README.md",
    ):
        p = PLUGIN_DIR / rel_path
        if not p.is_file() or not p.read_bytes().strip():
            errors.append(f"missing or empty {p.relative_to(REPO_ROOT)}")

    if not (REPO_ROOT / "scripts/record_cursor_marketplace_demo_evidence.py").is_file():
        errors.append("missing scripts/record_cursor_marketplace_demo_evidence.py")

    _scan_forbidden_placeholder_artifacts(errors)
    validate_approved_brand_source(errors)
    _validate_checklists(errors)


def _validate_checklists(errors: list[str]) -> None:
    for name in ("checklist-state.json", "checklist-evidence.json"):
        path = PUBLICATION_DIR / name
        if not path.is_file() or not path.read_bytes().strip():
            errors.append(f"missing or empty publication/{name}")
    if not CHECKLIST_STATE.is_file() or not CHECKLIST_EVIDENCE.is_file():
        return

    state = _read_json(CHECKLIST_STATE)
    evidence = _read_json(CHECKLIST_EVIDENCE)
    registry: dict[str, Any] = evidence.get("items", {})
    completed = state.get("completed", [])
    pending = state.get("pending", [])

    if not isinstance(completed, list) or not isinstance(pending, list):
        errors.append("checklist-state.json completed/pending must be arrays")
        return

    overlap = set(completed) & set(pending)
    if overlap:
        errors.append(f"checklist-state.json IDs in both completed and pending: {sorted(overlap)}")

    for item_id in completed:
        spec = registry.get(item_id)
        if not spec:
            errors.append(f"checklist-state completed id {item_id!r} has no evidence spec")
            continue
        if not _evidence_ok(spec):
            errors.append(f"checklist evidence failed for completed id {item_id!r}")

    for md_name in ("release-checklist.md", "pre-submit-checklist.md"):
        boxes = _parse_checkbox_ids(PUBLICATION_DIR / md_name)
        for item_id, is_checked in boxes.items():
            if is_checked and item_id not in completed:
                errors.append(f"{md_name}: checked id {item_id!r} not in checklist-state completed")
            if not is_checked and item_id in completed:
                errors.append(f"{md_name}: unchecked id {item_id!r} is marked completed in state file")

    go_ids = state.get("pre_submit_go", [])
    nogo_ids = state.get("pre_submit_nogo", [])
    if isinstance(go_ids, list):
        for item_id in go_ids:
            if item_id not in completed:
                errors.append(f"pre_submit_go id {item_id!r} must be in completed")
    if isinstance(nogo_ids, list):
        for item_id in nogo_ids:
            if item_id in completed:
                errors.append(f"pre_submit_nogo id {item_id!r} must not be in completed")
