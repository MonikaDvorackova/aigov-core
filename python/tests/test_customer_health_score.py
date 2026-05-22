"""Tests for scripts/customer_health_score.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "customer_health_score.py"
    spec = importlib.util.spec_from_file_location("customer_health_score", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def chs_mod():
    return _load_mod()


def test_sample_scores_stable(chs_mod):
    raw = (REPO_ROOT / "examples/customer-analytics/sample-customer-health.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    payload, code = chs_mod.compute_scores_from_dict(data)
    assert code == 0
    assert payload["ok"] is True
    assert payload["customer_id"] == "cust_sample_acme_001"
    assert payload["adoption_score"] == 89
    assert payload["risk_score"] == 42
    assert payload["expansion_score"] == 46
    assert payload["health_score"] == 70
    assert payload["renewal_signal"] == "medium"
    assert payload["findings"] == ["adoption_strong", "renewal_window_near", "risk_elevated"]
    out = chs_mod.dumps_json(payload)
    assert list(json.loads(out).keys()) == sorted(json.loads(out).keys())


def test_invalid_payload(chs_mod):
    payload, code = chs_mod.compute_scores_from_dict({})
    assert code == 1
    assert payload["ok"] is False


def test_subprocess_sample_input(chs_mod):
    import subprocess

    r = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "customer_health_score.py"),
            "--input",
            str(REPO_ROOT / "examples/customer-analytics/sample-customer-health.json"),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["health_score"] == 70
