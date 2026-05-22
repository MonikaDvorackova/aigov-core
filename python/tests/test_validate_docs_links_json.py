"""Tests for scripts/validate_docs_links.py JSON output."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "validate_docs_links.py"
    spec = importlib.util.spec_from_file_location("validate_docs_links", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vl_mod():
    return _load_mod()


def test_compute_docs_links_real_repo_strict(vl_mod):
    payload, code = vl_mod.compute_docs_links(REPO_ROOT, strict=True)
    assert code == 0
    assert payload["ok"] is True
    assert payload["strict"] is True
    assert payload["broken_links"] == []
    assert payload["warnings"] == []
    assert set(payload.keys()) == {"broken_links", "checked_files", "ok", "strict", "warnings"}
    raw = vl_mod.dumps_json(payload)
    assert json.loads(raw) == payload
    assert list(json.loads(raw).keys()) == sorted(json.loads(raw).keys())


def test_broken_link_detected_strict(vl_mod, tmp_path: Path):
    (tmp_path / "README.md").write_text("See [nope](./_missing_file_xyz_.md)\n", encoding="utf-8")
    payload, code = vl_mod.compute_docs_links(tmp_path, strict=True)
    assert code == 1
    assert payload["ok"] is False
    assert len(payload["broken_links"]) == 1
    row = payload["broken_links"][0]
    assert row["source"] == "README.md"
    assert row["target"] == "./_missing_file_xyz_.md"
    assert "missing" in str(row["reason"]).lower()


def test_broken_link_non_strict_exits_zero(vl_mod, tmp_path: Path):
    (tmp_path / "README.md").write_text("See [nope](./_missing_file_xyz_.md)\n", encoding="utf-8")
    payload, code = vl_mod.compute_docs_links(tmp_path, strict=False)
    assert code == 0
    assert payload["ok"] is False
    assert len(payload["broken_links"]) == 1


def test_json_subprocess_strict(tmp_path: Path):
    import subprocess

    (tmp_path / "README.md").write_text("# ok\n", encoding="utf-8")
    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "validate_docs_links.py"),
            "--strict",
            "--json",
            "--repo-root",
            str(tmp_path),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["ok"] is True
    assert data["strict"] is True
