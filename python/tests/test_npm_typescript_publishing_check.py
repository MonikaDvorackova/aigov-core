"""Tests for scripts/npm_typescript_publishing_check.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "npm_typescript_publishing_check.py"
    spec = importlib.util.spec_from_file_location("npm_typescript_publishing_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def npm_mod():
    return _load_mod()


def test_run_check_passes_on_current_repo(npm_mod) -> None:
    payload = npm_mod.run_check(REPO_ROOT)
    assert payload["ok"] is True
    assert payload["failures"] == []
    assert payload["version"] == 1
    assert "typescript-sdk/package.json" in payload["checked_paths"]
    assert "docs/releases/npm-typescript-publishing.md" in payload["checked_paths"]


def test_json_output_deterministic_shape(npm_mod) -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "npm_typescript_publishing_check.py"),
            "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert set(data.keys()) == {"checked_paths", "checks", "failures", "ok", "version"}
    assert data["ok"] is True
    assert list(data.keys()) == sorted(data.keys())
    raw = npm_mod.dumps_json(data)
    assert json.loads(raw) == data


def test_missing_package_json_field(npm_mod, tmp_path: Path) -> None:
    _seed_minimal_repo(tmp_path)
    pkg_path = tmp_path / "typescript-sdk" / "package.json"
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    del pkg["description"]
    pkg_path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")
    payload = npm_mod.run_check(tmp_path)
    assert payload["ok"] is False
    assert any("package_json_missing_field:description" in f for f in payload["failures"])


def test_missing_publishing_doc(npm_mod, tmp_path: Path) -> None:
    _seed_minimal_repo(tmp_path)
    doc = tmp_path / "docs/releases/npm-typescript-publishing.md"
    doc.unlink()
    payload = npm_mod.run_check(tmp_path)
    assert payload["ok"] is False
    assert any("missing_file:" in f and "npm-typescript-publishing.md" in f for f in payload["failures"])


def test_placeholder_metadata(npm_mod, tmp_path: Path) -> None:
    _seed_minimal_repo(tmp_path)
    pkg_path = tmp_path / "typescript-sdk" / "package.json"
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    pkg["description"] = "TODO: fill before publish"
    pkg_path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")
    payload = npm_mod.run_check(tmp_path)
    assert payload["ok"] is False
    assert any("package_json_placeholder:description" in f for f in payload["failures"])


def _seed_minimal_repo(tmp_path: Path) -> None:
    """Copy publishing artefacts from the real repo into an isolated temp tree."""
    import shutil

    for rel in (
        "typescript-sdk/package.json",
        "typescript-sdk/README.md",
        "typescript-sdk/tsconfig.json",
        "typescript-sdk/vitest.config.ts",
        "typescript-sdk/src/index.ts",
        "typescript-sdk/src/index.test.ts",
        "docs/releases/npm-typescript-publishing.md",
        "docs/releases/npm-typescript-publishing-manifest.json",
        "docs/reports/npm-typescript-publishing-readiness-audit.md",
        "scripts/npm_typescript_publishing_check.py",
        "LICENSE",
    ):
        src = REPO_ROOT / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
