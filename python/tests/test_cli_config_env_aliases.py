"""AIGOV_* env aliases for cli_config resolution."""

from __future__ import annotations

import pytest

from aigov_py import cli_config


def test_default_config_path_prefers_aigov_config(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    cfg = tmp_path / "aigov.json"
    monkeypatch.setenv("AIGOV_CONFIG", str(cfg))
    monkeypatch.setenv("GOVAI_CONFIG", str(tmp_path / "legacy.json"))
    assert cli_config.default_config_path() == cfg.resolve()


def test_resolve_audit_base_url_aigov_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "AIGOV_AUDIT_BASE_URL",
        "AIGOV_AUDIT_URL",
        "AIGOV_AUDIT_ENDPOINT",
        "AIGOV_BASE_URL",
        "GOVAI_AUDIT_BASE_URL",
        "GOVAI_BASE_URL",
    ):
        monkeypatch.delenv("AIGOV_AUDIT_BASE_URL", raising=False)
        monkeypatch.delenv("AIGOV_AUDIT_URL", raising=False)
        monkeypatch.delenv("AIGOV_AUDIT_ENDPOINT", raising=False)
        monkeypatch.delenv("AIGOV_BASE_URL", raising=False)
        monkeypatch.delenv("GOVAI_AUDIT_BASE_URL", raising=False)
        monkeypatch.delenv("GOVAI_BASE_URL", raising=False)
        monkeypatch.setenv(key, "http://example.test/")
        assert cli_config.resolve_audit_base_url(flag=None) == "http://example.test"


def test_resolve_api_key_prefers_aigov(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIGOV_API_KEY", "aigov-key")
    monkeypatch.setenv("GOVAI_API_KEY", "govai-key")
    assert cli_config.resolve_api_key(flag=None) == "aigov-key"
