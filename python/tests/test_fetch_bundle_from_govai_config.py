"""Config resolution for fetch_bundle_from_govai (no network)."""

from __future__ import annotations

import pytest

from aigov_py.fetch_bundle_from_govai import audit_base_url


def test_audit_base_url_prefers_aud_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIGOV_AUDIT_ENDPOINT", raising=False)
    monkeypatch.delenv("AIGOV_AUDIT_URL", raising=False)
    monkeypatch.delenv("GOVAI_AUDIT_BASE_URL", raising=False)
    monkeypatch.setenv("AUDIT_URL", "http://ledger.example:9999/")
    assert audit_base_url() == "http://ledger.example:9999"


def test_audit_base_url_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIGOV_AUDIT_ENDPOINT", "http://ep/")
    monkeypatch.setenv("AIGOV_AUDIT_URL", "http://url/")
    monkeypatch.setenv("GOVAI_AUDIT_BASE_URL", "http://govai/")
    monkeypatch.setenv("AUDIT_URL", "http://audit/")
    assert audit_base_url() == "http://ep"
