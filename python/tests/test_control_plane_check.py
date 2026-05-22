"""Tests for enterprise ``scripts/control_plane_check.py`` (machine-readable governance bundle)."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "control_plane_check.py"
    spec = importlib.util.spec_from_file_location("control_plane_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def cpc_mod():
    return _load_mod()


def test_valid_control_plane_package_passes(cpc_mod):
    payload, code = cpc_mod.validate_enterprise(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["failures"] == []
    raw = cpc_mod.dumps_json({k: v for k, v in payload.items() if k != "human_summary"})
    assert json.loads(raw) == {k: v for k, v in payload.items() if k != "human_summary"}


def _copy_bundle(dest: Path) -> None:
    src = REPO_ROOT / "control-plane"
    shutil.copytree(src, dest / "control-plane")


def test_duplicate_role_ids_fail(cpc_mod, tmp_path: Path):
    _copy_bundle(tmp_path)
    rt_path = tmp_path / "control-plane" / "role-taxonomy.json"
    data = json.loads(rt_path.read_text(encoding="utf-8"))
    data["roles"][1]["role_id"] = data["roles"][0]["role_id"]
    rt_path.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    payload, code = cpc_mod.validate_enterprise(tmp_path)
    assert code == 1
    assert any("duplicate_role_id" in f for f in payload["failures"])


def test_missing_required_field_fails(cpc_mod, tmp_path: Path):
    _copy_bundle(tmp_path)
    rt_path = tmp_path / "control-plane" / "role-taxonomy.json"
    data = json.loads(rt_path.read_text(encoding="utf-8"))
    del data["schema_id"]
    rt_path.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    payload, code = cpc_mod.validate_enterprise(tmp_path)
    assert code == 1
    assert any("schema_id" in f for f in payload["failures"])


def test_invalid_delegation_reference_fails(cpc_mod, tmp_path: Path):
    _copy_bundle(tmp_path)
    dm_path = tmp_path / "control-plane" / "delegation-model.json"
    data = json.loads(dm_path.read_text(encoding="utf-8"))
    data["delegations"][0]["from_role_id"] = "r.govai.nonexistent"
    dm_path.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    payload, code = cpc_mod.validate_enterprise(tmp_path)
    assert code == 1
    assert any("delegation_unknown_from_role" in f for f in payload["failures"])


def test_invalid_escalation_reference_fails(cpc_mod, tmp_path: Path):
    _copy_bundle(tmp_path)
    em_path = tmp_path / "control-plane" / "escalation-model.json"
    data = json.loads(em_path.read_text(encoding="utf-8"))
    data["escalation_paths"][0]["steps"][0]["escalation_id"] = "esc.govai.nonexistent"
    em_path.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    payload, code = cpc_mod.validate_enterprise(tmp_path)
    assert code == 1
    assert any("escalation_path_step_unknown_escalation" in f for f in payload["failures"])
