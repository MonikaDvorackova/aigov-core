"""Tests for scripts/run_fail_closed_demo.py (imported via importlib)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_fail_closed_mod():
    path = REPO_ROOT / "scripts" / "run_fail_closed_demo.py"
    spec = importlib.util.spec_from_file_location("run_fail_closed_demo", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def fc_mod():
    return _load_fail_closed_mod()


def test_build_summary_keys_sorted_json(fc_mod):
    s = fc_mod.build_summary(
        ok=True,
        ready_http_code=200,
        ready_error=None,
        blocked_script_exit_code=0,
        blocked_verdict_confirmed=True,
        audit_base_url="http://127.0.0.1:8088",
        reason=None,
    )
    raw = fc_mod.dumps_json(s)
    parsed = json.loads(raw)
    assert parsed["ok"] is True
    assert parsed["blocked_verdict_confirmed"] is True
    assert parsed["govai_check_exit_code"] == 3
    assert parsed["ready_http_code"] == 200
    assert list(parsed.keys()) == sorted(parsed.keys())
    assert raw == fc_mod.dumps_json(parsed)


def test_non_loopback_fails(fc_mod, tmp_path: Path):
    summary, code = fc_mod.run_demo(
        repo_root=tmp_path,
        audit_base_url="http://example.com",
        api_key="k",
        project=None,
        timeout=1.0,
    )
    assert code == 1
    assert summary["ok"] is False
    assert summary["reason"] == "non_loopback_url"


def test_missing_api_key(fc_mod, tmp_path: Path):
    summary, code = fc_mod.run_demo(
        repo_root=tmp_path,
        audit_base_url="http://127.0.0.1:8088",
        api_key="",
        project=None,
        timeout=1.0,
    )
    assert code == 1
    assert summary["reason"] == "missing_govai_api_key"


def test_ready_not_200(fc_mod, tmp_path: Path):
    with patch.object(fc_mod, "get_ready_http_code", return_value=(503, None)):
        summary, code = fc_mod.run_demo(
            repo_root=tmp_path,
            audit_base_url="http://127.0.0.1:8088",
            api_key="test-key",
            project=None,
            timeout=1.0,
        )
    assert code == 2
    assert summary["ok"] is False
    assert summary["ready_http_code"] == 503
    assert summary["reason"] == "ready_not_200"
    assert summary["blocked_deployment_sh_exit_code"] is None


def test_blocked_script_success(fc_mod, tmp_path: Path):
    with (
        patch.object(fc_mod, "get_ready_http_code", return_value=(200, None)),
        patch.object(fc_mod, "run_blocked_deployment", return_value=0),
    ):
        summary, code = fc_mod.run_demo(
            repo_root=tmp_path,
            audit_base_url="http://127.0.0.1:8088",
            api_key="test-key",
            project="github-actions",
            timeout=1.0,
        )
    assert code == 0
    assert summary["ok"] is True
    assert summary["blocked_verdict_confirmed"] is True
    assert summary["blocked_deployment_sh_exit_code"] == 0


def test_blocked_script_unexpected_nonzero(fc_mod, tmp_path: Path):
    with (
        patch.object(fc_mod, "get_ready_http_code", return_value=(200, None)),
        patch.object(fc_mod, "run_blocked_deployment", return_value=1),
    ):
        summary, code = fc_mod.run_demo(
            repo_root=tmp_path,
            audit_base_url="http://127.0.0.1:8088",
            api_key="test-key",
            project=None,
            timeout=1.0,
        )
    assert code == 3
    assert summary["ok"] is False
    assert summary["blocked_verdict_confirmed"] is False
    assert summary["reason"] == "blocked_script_failed"
    assert summary["govai_check_exit_code"] is None
