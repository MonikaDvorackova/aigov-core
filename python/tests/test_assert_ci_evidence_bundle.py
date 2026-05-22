"""Tests for CI evidence bundle guards."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aigov_py import assert_ci_evidence_bundle as mod


def test_assert_rejects_ci_fallback_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "_repo_root", lambda: tmp_path)
    ev = tmp_path / "docs" / "evidence"
    ev.mkdir(parents=True)
    rid = "r-fallback"
    payload = {
        "run_id": rid,
        "events": [
            {"event_type": "evidence_genesis"},
            {"event_type": "ci_fallback_used"},
        ],
    }
    (ev / f"{rid}.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SystemExit, match="ci_fallback_used"):
        mod.assert_non_fallback_bundle(rid)


def test_assert_requires_discovery_and_evaluation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "_repo_root", lambda: tmp_path)
    ev = tmp_path / "docs" / "evidence"
    ev.mkdir(parents=True)
    rid = "r-no-discovery"
    payload = {
        "run_id": rid,
        "events": [{"event_type": "run_started"}, {"event_type": "evaluation_reported"}],
    }
    (ev / f"{rid}.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SystemExit, match="ai_discovery_reported"):
        mod.assert_non_fallback_bundle(rid)


def test_assert_ok_fullish_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "_repo_root", lambda: tmp_path)
    ev = tmp_path / "docs" / "evidence"
    ev.mkdir(parents=True)
    rid = "r-ok"
    payload = {
        "run_id": rid,
        "events": [
            {"event_type": "run_started"},
            {"event_type": "evaluation_reported"},
            {"event_type": "ai_discovery_reported"},
        ],
    }
    (ev / f"{rid}.json").write_text(json.dumps(payload), encoding="utf-8")
    mod.assert_non_fallback_bundle(rid)
