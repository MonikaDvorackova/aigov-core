from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_repo_root_module_entrypoint_policy_compile() -> None:
    """
    Ensure `python -m aigov_py.cli ...` from repo root runs in-repo CLI (not site-packages).
    """
    repo_root = Path(__file__).resolve().parents[2]
    policy_path = repo_root / "docs" / "policies" / "ai-act-high-risk.example.yaml"

    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "aigov_py.cli",
            "policy",
            "compile",
            "--path",
            str(policy_path),
        ],
        cwd=str(repo_root),
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
    assert "evaluation_reported" in lines
    assert lines == sorted(lines)

    rj = subprocess.run(
        [
            sys.executable,
            "-m",
            "aigov_py.cli",
            "policy",
            "compile",
            "--path",
            str(policy_path),
            "--json",
        ],
        cwd=str(repo_root),
        check=True,
        capture_output=True,
        text=True,
    )
    obj = json.loads(rj.stdout)
    assert obj["policy"]["id"] == "ai-act-high-risk"
    assert isinstance(obj["required_evidence"], list)

