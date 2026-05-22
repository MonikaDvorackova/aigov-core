"""Tests for scripts/validate_changelog.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_changelog.py"
    spec = importlib.util.spec_from_file_location("validate_changelog", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vch_mod():
    return _load_mod()


def test_validate_real_changelog(vch_mod):
    payload, code = vch_mod.validate_changelog(REPO_ROOT, "CHANGELOG.md")
    assert code == 0
    assert payload["ok"] is True
    raw = vch_mod.dumps_json(payload)
    assert json.loads(raw) == payload
    assert list(json.loads(raw).keys()) == sorted(json.loads(raw).keys())


def test_changelog_without_unreleased_fails(vch_mod, tmp_path: Path):
    p = tmp_path / "CHANGELOG.md"
    p.write_text(
        "# Changelog\n\n## [1.0.0] - 2020-01-01\n\n### Added\n\n- x\n",
        encoding="utf-8",
    )
    payload, code = vch_mod.validate_changelog(tmp_path, "CHANGELOG.md")
    assert code == 1
    assert payload["ok"] is False
    assert "missing_unreleased_heading" in payload["errors"]


def test_subprocess_validate_changelog():
    import subprocess

    r = subprocess.run(
        ["python3", str(REPO_ROOT / "scripts" / "validate_changelog.py"), "--json", "--repo-root", str(REPO_ROOT)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
