"""Tests for scripts/oss_diagnostics.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _fake_git_reports_diffs(three_dot_out: str, worktree_out: str, untracked_out: str = ""):
    """Fake _git_output: rev-parse ok; ls-files untracked; diff ...HEAD vs plain base for docs/reports/."""

    def fake_git(repo: Path, *args: str) -> tuple[int, str]:
        if args[0] == "rev-parse":
            return 0, "deadbeef"
        if args[0] == "ls-files":
            return 0, untracked_out
        if args[0] == "diff" and len(args) >= 2:
            if "..." in args[1]:
                return 0, three_dot_out
            return 0, worktree_out
        return 99, ""

    return fake_git


def _load_mod():
    path = REPO_ROOT / "scripts" / "oss_diagnostics.py"
    spec = importlib.util.spec_from_file_location("oss_diagnostics", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def od_mod():
    return _load_mod()


def test_run_diagnostics_real_repo_ok_and_stable_keys(od_mod):
    # Missing base ref skips docs/reports diff enforcement (warning only), keeping this test stable across branches.
    payload, code = od_mod.run_diagnostics(REPO_ROOT, "origin/__nonexistent_for_diagnostics__")
    assert isinstance(payload["checks"], list)
    assert isinstance(payload["failures"], list)
    assert isinstance(payload["warnings"], list)
    assert "repo_root" in payload
    assert code == (0 if payload["ok"] else 1)
    raw = od_mod.dumps_json(payload)
    data = json.loads(raw)
    assert list(data.keys()) == sorted(data.keys())
    for chk in data["checks"]:
        assert list(chk.keys()) == sorted(chk.keys())


def test_run_diagnostics_empty_dir_fails(od_mod, tmp_path: Path):
    payload, code = od_mod.run_diagnostics(tmp_path, "origin/__nonexistent_for_diagnostics__")
    assert payload["ok"] is False
    assert code == 1
    assert any("required_oss_files" in f for f in payload["failures"])


def test_dashboard_public_docs_fails_without_dashboard_docs(od_mod, tmp_path: Path):
    """Minimal tree: repo_root exists and git ref missing (warn), but dashboard public docs paths missing fails check."""
    (tmp_path / "README.md").write_text("# x", encoding="utf-8")
    payload, code = od_mod.run_diagnostics(tmp_path, "origin/__missing__")
    assert code == 1
    ids = {c["id"]: c["ok"] for c in payload["checks"]}
    assert ids.get("dashboard_public_docs") is False


def test_check_docs_reports_multiple_md_paths_fail(od_mod, tmp_path: Path):
    body = "docs/reports/a.md\ndocs/reports/b.md"
    fake_git = _fake_git_reports_diffs(body, body)

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, _ = od_mod.check_docs_reports_vs_base(tmp_path, "origin/staging")
    assert ok is False
    assert detail == "multiple_docs_reports_md_diff:2:docs/reports/a.md,docs/reports/b.md"


def test_check_docs_reports_single_custom_documentation_frontend_passes(od_mod, tmp_path: Path):
    path = "docs/reports/custom_documentation_frontend.md"
    fake_git = _fake_git_reports_diffs(path, path)

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, _ = od_mod.check_docs_reports_vs_base(tmp_path, "origin/staging")
    assert ok is True
    assert detail == "single_docs_report_diff:docs/reports/custom_documentation_frontend.md"


def test_check_docs_reports_single_non_phase_basename_passes(od_mod, tmp_path: Path):
    """No phase6/phase7/phase8/Mintlify basename is required — any single ``*.md`` under docs/reports/."""
    path = "docs/reports/other.md"
    fake_git = _fake_git_reports_diffs(path, path)

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, _ = od_mod.check_docs_reports_vs_base(tmp_path, "origin/staging")
    assert ok is True
    assert detail == "single_docs_report_diff:docs/reports/other.md"


def test_check_docs_reports_single_arbitrary_uuid_style_passes(od_mod, tmp_path: Path):
    path = "docs/reports/2c4f7c6e-0d1a-4c9d-8f86-9b5c6f6a8c2a.md"
    fake_git = _fake_git_reports_diffs(path, path)

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, _ = od_mod.check_docs_reports_vs_base(tmp_path, "origin/staging")
    assert ok is True
    assert detail == f"single_docs_report_diff:{path}"


def test_check_docs_reports_no_md_diff_fail(od_mod, tmp_path: Path):
    fake_git = _fake_git_reports_diffs("", "")

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, warns = od_mod.check_docs_reports_vs_base(tmp_path, "origin/staging")
    assert ok is False
    assert detail == "no_docs_reports_md_diff"
    assert any("no_docs_reports_diff_vs_base_ref" in w for w in warns)


def test_check_docs_reports_only_non_md_fail(od_mod, tmp_path: Path):
    body = "docs/reports/manifest.json"
    fake_git = _fake_git_reports_diffs(body, body)

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, warns = od_mod.check_docs_reports_vs_base(tmp_path, "origin/staging")
    assert ok is False
    assert detail == "no_docs_reports_md_diff"
    assert any("docs_reports_three_dot_has_no_markdown" in w for w in warns)
    assert any("docs_reports_worktree_has_no_markdown" in w for w in warns)


def test_check_docs_reports_worktree_fallback_single(od_mod, tmp_path: Path):
    eco = "docs/reports/feature-audit.md"
    fake_git = _fake_git_reports_diffs("", eco)

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, warns = od_mod.check_docs_reports_vs_base(tmp_path, "origin/staging")
    assert ok is True
    assert detail == "single_docs_report_diff:docs/reports/feature-audit.md"
    assert any("docs_reports_diff_used_worktree_fallback_vs_base" in w for w in warns)


def test_check_docs_reports_untracked_only_single(od_mod, tmp_path: Path):
    eco = "docs/reports/untracked-only.md"
    fake_git = _fake_git_reports_diffs("", "", untracked_out=eco)

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, warns = od_mod.check_docs_reports_vs_base(tmp_path, "origin/staging")
    assert ok is True
    assert detail == "single_docs_report_diff:docs/reports/untracked-only.md"
    assert any("docs_reports_diff_used_worktree_fallback_vs_base" in w for w in warns)


def test_check_docs_reports_untracked_two_md_fail(od_mod, tmp_path: Path):
    fake_git = _fake_git_reports_diffs(
        "",
        "",
        untracked_out="docs/reports/a.md\ndocs/reports/b.md",
    )

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, _ = od_mod.check_docs_reports_vs_base(tmp_path, "origin/staging")
    assert ok is False
    assert detail == "multiple_docs_reports_md_diff:2:docs/reports/a.md,docs/reports/b.md"


def test_docs_report_diff_normal_mode_zero_fails(od_mod, tmp_path: Path):
    fake_git = _fake_git_reports_diffs("", "")

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, _ = od_mod.check_docs_reports_vs_base(
            tmp_path, "origin/staging", release_promotion_mode=False
        )
    assert ok is False
    assert detail == "no_docs_reports_md_diff"


def test_docs_report_diff_normal_mode_multiple_fails(od_mod, tmp_path: Path):
    body = "docs/reports/a.md\ndocs/reports/b.md"
    fake_git = _fake_git_reports_diffs(body, body)

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, _ = od_mod.check_docs_reports_vs_base(
            tmp_path, "origin/staging", release_promotion_mode=False
        )
    assert ok is False
    assert detail == "multiple_docs_reports_md_diff:2:docs/reports/a.md,docs/reports/b.md"


def test_docs_report_diff_release_promotion_zero_passes(od_mod, tmp_path: Path):
    fake_git = _fake_git_reports_diffs("", "")

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, _ = od_mod.check_docs_reports_vs_base(
            tmp_path, "origin/staging", release_promotion_mode=True
        )
    assert ok is True
    assert detail == "release_promotion_docs_report_diff:0"


def test_docs_report_diff_release_promotion_multiple_passes(od_mod, tmp_path: Path):
    body = "docs/reports/a.md\ndocs/reports/b.md"
    fake_git = _fake_git_reports_diffs(body, body)

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, _ = od_mod.check_docs_reports_vs_base(
            tmp_path, "origin/staging", release_promotion_mode=True
        )
    assert ok is True
    assert detail == "release_promotion_docs_report_diff:2"


def test_check_docs_reports_superseded_iso_audit_excluded_from_count(od_mod, tmp_path: Path):
    """Branch history may add then delete iso-42001-readiness-audit.md; only consolidated report counts."""
    body = "docs/reports/iso-42001-readiness-audit.md\ndocs/reports/repo-debt-audit-and-cleanup.md"
    fake_git = _fake_git_reports_diffs(body, body)

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, _ = od_mod.check_docs_reports_vs_base(tmp_path, "origin/staging")
    assert ok is True
    assert detail == "single_docs_report_diff:docs/reports/repo-debt-audit-and-cleanup.md"


def test_check_docs_reports_three_dot_one_untracked_extra_fails(od_mod, tmp_path: Path):
    one = "docs/reports/repo-debt-audit-and-cleanup.md"
    fake_git = _fake_git_reports_diffs(one, one, untracked_out="docs/reports/extra.md")

    with patch.object(od_mod, "_git_output", fake_git):
        ok, detail, _ = od_mod.check_docs_reports_vs_base(tmp_path, "origin/staging")
    assert ok is False
    assert detail == "multiple_docs_reports_md_diff:2:docs/reports/extra.md,docs/reports/repo-debt-audit-and-cleanup.md"


def test_subprocess_json():
    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "oss_diagnostics.py"),
            "--json",
            "--repo-root",
            str(REPO_ROOT),
            "--base-ref",
            "origin/__nonexistent_for_diagnostics__",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    line = r.stdout.strip().splitlines()[-1]
    data = json.loads(line)
    assert data["ok"] is True
    assert "git_base_ref_missing" in "".join(data["warnings"])
