"""Tests for scripts/public_sdk_packages_check.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_mod():
    path = REPO_ROOT / "scripts" / "public_sdk_packages_check.py"
    spec = importlib.util.spec_from_file_location("public_sdk_packages_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def sdk_mod():
    return _load_mod()


def test_compute_real_repo_ok(sdk_mod):
    payload, code = sdk_mod.compute_public_sdk_packages(REPO_ROOT)
    assert code == 0
    assert payload["ok"] is True
    assert payload["score"] == 100
    assert payload["failures"] == []
    raw = sdk_mod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_public_functions_sdk_package_allowed(sdk_mod, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_minimal_sdk_repo(sdk_mod, root, pkg_text=_PUBLIC_FUNCTIONS_SDK_PACKAGE_JSON)
    payload, code = sdk_mod.compute_public_sdk_packages(root)
    assert code == 0
    assert payload["ok"] is True
    assert sdk_mod._is_public_functions_sdk_package(_PUBLIC_FUNCTIONS_SDK_PACKAGE_JSON)


_PUBLIC_FUNCTIONS_SDK_PACKAGE_JSON = """{
  "name": "@govai/functions-sdk",
  "version": "0.1.0",
  "publishConfig": { "access": "public" },
  "files": ["dist", "README.md"]
}
"""


def _write_minimal_sdk_repo(sdk_mod, root: Path, *, pkg_text: str) -> None:
    safe_doc = "GovAIClient\nexportAudit\n@govai/functions-sdk\nRust Core\n"
    for rel in set(sdk_mod.REQUIRED_PATHS) | set(sdk_mod.CLAIM_SCAN_PATHS):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(safe_doc, encoding="utf-8")
    (root / "typescript-sdk/src/client.ts").parent.mkdir(parents=True, exist_ok=True)
    (root / "typescript-sdk/src/client.ts").write_text("// GovAIClient exportAudit\n", encoding="utf-8")
    (root / "typescript-sdk/src/index.test.ts").write_text("// tests\n", encoding="utf-8")
    (root / "typescript-sdk/package.json").write_text(pkg_text, encoding="utf-8")
    (root / "Makefile").write_text(
        "public-sdk-packages-check:\n"
        "sdk-ecosystem-check:\n"
        "typescript-client-check:\n",
        encoding="utf-8",
    )
    audit = root / sdk_mod.AUDIT_REPORT
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text("## Evaluation gate\n## Human approval gate\n", encoding="utf-8")


def test_forbidden_rust_sdk_label_fails(sdk_mod, tmp_path: Path):
    root = tmp_path / "repo"
    (root / "dashboard/lib/landing").mkdir(parents=True)
    (root / "dashboard/lib/landing/govaiWorkflowStages.ts").write_text(
        'export const GOVAI_CONNECTORS = [{ label: "Rust SDK" }];',
        encoding="utf-8",
    )
    for rel in sdk_mod.REQUIRED_PATHS:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("GovAIClient\nexportAudit\ntypescript-sdk/\n", encoding="utf-8")
    (root / "typescript-sdk/src/client.ts").parent.mkdir(parents=True, exist_ok=True)
    (root / "typescript-sdk/src/client.ts").write_text("// GovAIClient exportAudit\n", encoding="utf-8")
    (root / "typescript-sdk/src/validate.ts").write_text("// validate\n", encoding="utf-8")
    (root / "typescript-sdk/package.json").write_text("{}", encoding="utf-8")
    (root / "Makefile").write_text(
        "public-sdk-packages-check:\n"
        "sdk-ecosystem-check:\n"
        "typescript-client-check:\n",
        encoding="utf-8",
    )
    (root / "dashboard/lib/landing/landingPageContent.ts").write_text(
        "Rust Core\n", encoding="utf-8"
    )
    payload, code = sdk_mod.compute_public_sdk_packages(root)
    assert code == 1
    assert payload["ok"] is False
    assert any("rust_sdk_label" in f for f in payload["failures"])
