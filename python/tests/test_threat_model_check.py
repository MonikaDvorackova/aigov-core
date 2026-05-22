"""Tests for scripts/threat_model_check.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_tm():
    path = REPO_ROOT / "scripts" / "threat_model_check.py"
    spec = importlib.util.spec_from_file_location("threat_model_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tm():
    return _load_tm()


def test_validate_sample_real_repo(tm):
    ok, failures = tm.validate_sample(REPO_ROOT, "examples/security/sample-threat-matrix.json")
    assert ok is True
    assert failures == []


def test_validate_sample_missing_category(tm, tmp_path: Path):
    p = tmp_path / "t.json"
    p.write_text(
        json.dumps(
            {
                "categories": [
                    {
                        "adversary_capability": "x",
                        "id": "insider_tampering",
                        "in_scope": True,
                        "mitigation": "m",
                        "out_of_scope": "o",
                        "residual_risk": "r",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    ok, failures = tm.validate_sample(tmp_path, "t.json")
    assert ok is False
    assert any("missing_category" in f for f in failures)


def test_subprocess_threat_model_json():
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "threat_model_check.py"), "--json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["ok"] is True
