"""Tests for scripts/observability_check.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "observability_check.py"
    spec = importlib.util.spec_from_file_location("observability_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def obs_mod():
    return _load_mod()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _valid_schema() -> dict:
    return json.loads((REPO_ROOT / "observability/runtime-event-schema.json").read_text(encoding="utf-8"))


def _valid_examples() -> dict:
    return json.loads((REPO_ROOT / "observability/runtime-event-examples.json").read_text(encoding="utf-8"))


def _valid_metrics() -> dict:
    return json.loads((REPO_ROOT / "observability/dashboard-metrics.json").read_text(encoding="utf-8"))


def _valid_incidents() -> dict:
    return json.loads((REPO_ROOT / "observability/incident-taxonomy.json").read_text(encoding="utf-8"))


def _make_valid_repo(tmp_path: Path, obs_mod) -> Path:
    _write_json(tmp_path / "observability/runtime-event-schema.json", _valid_schema())
    _write_json(tmp_path / "observability/runtime-event-examples.json", _valid_examples())
    _write_json(tmp_path / "observability/dashboard-metrics.json", _valid_metrics())
    _write_json(tmp_path / "observability/incident-taxonomy.json", _valid_incidents())
    _write_json(
        tmp_path / "examples/observability/sample-dashboard-summary.json",
        json.loads((REPO_ROOT / "examples/observability/sample-dashboard-summary.json").read_text(encoding="utf-8")),
    )
    (tmp_path / "examples/observability/sample-runtime-events.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "examples/observability/sample-runtime-events.jsonl").write_text(
        (REPO_ROOT / "examples/observability/sample-runtime-events.jsonl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    for rel_path in obs_mod.REQUIRED_DOCS:
        full = tmp_path / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("# placeholder\n", encoding="utf-8")
    (tmp_path / "Makefile").write_text(
        ".PHONY: observability-check\nobservability-check:\n\t@true\n",
        encoding="utf-8",
    )
    return tmp_path


def test_successful_validation(obs_mod, tmp_path: Path):
    repo_root = _make_valid_repo(tmp_path, obs_mod)
    payload, code = obs_mod.validate_observability(repo_root)
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    names = sorted(c["name"] for c in payload["checks"])
    assert names == sorted(
        [
            "dashboard_metrics",
            "dashboard_summary",
            "documentation_paths",
            "incident_taxonomy",
            "makefile_wiring",
            "runtime_event_examples",
            "runtime_event_schema",
        ]
    )
    assert payload["checked_paths"] == sorted(payload["checked_paths"])
    assert payload["checks"] == sorted(payload["checks"], key=lambda c: c["name"])
    assert not payload["failures"]


def test_duplicate_metric_ids_fail(obs_mod, tmp_path: Path):
    repo_root = _make_valid_repo(tmp_path, obs_mod)
    metrics = _valid_metrics()
    metrics["metrics"][1]["id"] = metrics["metrics"][0]["id"]
    _write_json(repo_root / "observability/dashboard-metrics.json", metrics)

    payload, code = obs_mod.validate_observability(repo_root)

    assert code == 1
    assert payload["ok"] is False
    assert "metrics:duplicate_id:runtime_evaluations_total" in payload["failures"]


def test_missing_required_event_fields_fail(obs_mod, tmp_path: Path):
    repo_root = _make_valid_repo(tmp_path, obs_mod)
    examples = _valid_examples()
    del examples["examples"][0]["run_id"]
    _write_json(repo_root / "observability/runtime-event-examples.json", examples)

    payload, code = obs_mod.validate_observability(repo_root)

    assert code == 1
    assert payload["ok"] is False
    assert "examples[0]:missing_required_field:run_id" in payload["failures"]


def test_invalid_incident_taxonomy_fails(obs_mod, tmp_path: Path):
    repo_root = _make_valid_repo(tmp_path, obs_mod)
    incidents = _valid_incidents()
    incidents["classes"][1]["class_id"] = incidents["classes"][0]["class_id"]
    incidents["classes"][0]["default_severity"] = "page"
    _write_json(repo_root / "observability/incident-taxonomy.json", incidents)

    payload, code = obs_mod.validate_observability(repo_root)

    assert code == 1
    assert payload["ok"] is False
    assert "incidents:duplicate_class_id:governance_policy_gap" in payload["failures"]
    assert "incidents[0]:invalid_default_severity" in payload["failures"]
