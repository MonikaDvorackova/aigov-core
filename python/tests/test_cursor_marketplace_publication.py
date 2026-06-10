"""Tests for Cursor Marketplace publication validation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
PLUGIN = REPO_ROOT / ".cursor-plugin"
PUBLICATION = PLUGIN / "publication"
MANIFEST = PLUGIN / "assets" / "marketplace-assets.json"

sys.path.insert(0, str(SCRIPTS))
from cursor_marketplace_publication import (  # noqa: E402
    ASSET_STATUSES,
    validate_publication_package,
)


def test_publication_status_declares_not_live():
    text = (PUBLICATION / "status.md").read_text(encoding="utf-8")
    assert "Internally usable" in text
    assert "aigov-mark.ico" in text
    assert "Not live" in text
    assert "not approved" in text.lower()


def test_marketplace_assets_manifest_states():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["publication_state"] == "pre_submit_not_live"
    assert data["installation_model"] == "full_repository_required_for_mcp"
    statuses = {a["status"] for a in data["assets"]}
    assert statuses <= set(ASSET_STATUSES)
    by_id = {a["id"]: a for a in data["assets"]}
    assert data.get("approved_brand_source") == "dashboard/brand/aigov-mark.ico"
    assert by_id["logo"]["status"] == "committed"
    assert by_id["hero"]["status"] == "committed"
    assert by_id["demo_flow_evidence"]["status"] == "committed"
    screenshots = [a for a in data["assets"] if a["role"] == "listing_screenshot"]
    assert len(screenshots) == 5
    assert all(a["status"] == "committed" for a in screenshots)
    assert "generated_preview" not in statuses
    assert "pending_real_capture" not in statuses


def test_validate_publication_package_passes_without_listing_media():
    errors: list[str] = []
    validate_publication_package(errors, require_listing_media=False)
    assert errors == [], "\n".join(errors)


def test_validate_publication_package_passes_with_committed_listing_media():
    errors: list[str] = []
    validate_publication_package(errors, require_listing_media=True)
    assert errors == [], "\n".join(errors)


def test_validate_cursor_plugin_script_passes():
    script = SCRIPTS / "validate_cursor_plugin.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_validate_listing_media_script_passes_when_committed():
    script = SCRIPTS / "validate_cursor_marketplace_listing.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_installation_check_reports_full_repository():
    mcp = REPO_ROOT / "mcp" / "aigov_mcp_server.py"
    proc = subprocess.run(
        [sys.executable, str(mcp), "installation-check"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["installation_mode"] == "full_repository"
    assert body["mcp_tools_available"] is True
