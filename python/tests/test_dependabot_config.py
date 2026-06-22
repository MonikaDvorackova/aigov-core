"""Tests for Dependabot staging target configuration."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_dependabot_config.py"
DEPENDABOT_YML = ROOT / ".github" / "dependabot.yml"


def _load_validator():
    spec = importlib.util.spec_from_file_location("check_dependabot_config", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dependabot_yml_targets_staging_for_all_ecosystems() -> None:
    text = DEPENDABOT_YML.read_text(encoding="utf-8")
    assert "target-branch: stagingtarget-branch:" not in text

    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "cargo" in proc.stdout
    assert "pip" in proc.stdout


def test_dependabot_validator_rejects_root_level_target_branch() -> None:
    validator = _load_validator()
    bad = DEPENDABOT_YML.read_text(encoding="utf-8").replace(
        "    target-branch: staging\n    schedule:",
        "target-branch: staging\n    schedule:",
        1,
    )
    tmp = ROOT / ".github" / ".dependabot-test-bad.yml"
    tmp.write_text(bad, encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="must be indented"):
            validator.validate_dependabot_config(tmp)
    finally:
        tmp.unlink(missing_ok=True)
