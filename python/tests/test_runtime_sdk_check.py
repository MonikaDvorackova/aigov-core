from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_runtime_sdk_check_module():
    root = Path(__file__).resolve().parents[2]
    path = root / "scripts" / "runtime_sdk_check.py"
    spec = importlib.util.spec_from_file_location("runtime_sdk_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_run_all_checks_passes_on_repo() -> None:
    rsc = _load_runtime_sdk_check_module()
    repo = Path(__file__).resolve().parents[2]
    doc = rsc.run_all_checks(repo)
    assert doc["ok"] is True
    assert doc["checks"]["required_files_missing"] == []


def test_run_all_checks_detects_missing_file(tmp_path: Path) -> None:
    rsc = _load_runtime_sdk_check_module()
    repo = tmp_path
    (repo / "python" / "aigov_py" / "runtime").mkdir(parents=True)
    for name in ("__init__.py", "client.py", "models.py", "exceptions.py"):
        (repo / "python" / "aigov_py" / "runtime" / name).write_text("# stub\n", encoding="utf-8")
    (repo / "python" / "aigov_py" / "runtime" / "adapters").mkdir(parents=True)
    for name in ("__init__.py", "fastapi.py", "langchain.py", "openai_gateway.py"):
        (repo / "python" / "aigov_py" / "runtime" / "adapters" / name).write_text("# stub\n", encoding="utf-8")
    doc = rsc.run_all_checks(repo)
    assert doc["ok"] is False
    assert doc["checks"]["required_files_missing"]
