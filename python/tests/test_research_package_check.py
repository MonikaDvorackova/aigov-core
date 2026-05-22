"""Tests for scripts/research_package_check.py and scripts/validate_research_manifest.py."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_validate():
    path = REPO_ROOT / "scripts" / "validate_research_manifest.py"
    spec = importlib.util.spec_from_file_location("validate_research_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_check():
    path = REPO_ROOT / "scripts" / "research_package_check.py"
    spec = importlib.util.spec_from_file_location("research_package_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vmod():
    return _load_validate()


@pytest.fixture(scope="module")
def cmod():
    return _load_check()


def test_validate_real_manifest(vmod):
    payload, code = vmod.validate_manifest(REPO_ROOT, "research/research-manifest.json")
    assert code == 0
    assert payload["ok"] is True
    assert not payload["errors"]
    raw = vmod.dumps_json(payload)
    assert json.loads(raw) == payload


def test_research_package_check_real_repo(cmod):
    payload, code = cmod.run_check(REPO_ROOT, "research/research-manifest.json")
    assert code == 0
    assert payload["ok"] is True


def test_validate_missing_manifest(vmod, tmp_path: Path):
    payload, code = vmod.validate_manifest(tmp_path, "research/research-manifest.json")
    assert code == 1
    assert payload["ok"] is False


def test_validate_missing_required_key(vmod, tmp_path: Path):
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "research-manifest.json").write_text(
        json.dumps({"package_id": "x"}),
        encoding="utf-8",
    )
    payload, code = vmod.validate_manifest(tmp_path, "research/research-manifest.json")
    assert code == 1
    assert any("missing_required_key" in e for e in payload["errors"])


def test_validate_broken_cross_reference(vmod, tmp_path: Path):
    root = tmp_path
    shutil.copytree(REPO_ROOT / "research", root / "research")
    shutil.copytree(REPO_ROOT / "docs" / "research", root / "docs" / "research")
    shutil.copytree(REPO_ROOT / "examples" / "research", root / "examples" / "research")
    shutil.copytree(REPO_ROOT / "benchmarks", root / "benchmarks")
    cit_path = root / "research" / "citation-metadata.json"
    cit = json.loads(cit_path.read_text(encoding="utf-8"))
    refs = dict(cit["cross_references"])
    refs["broken_helper"] = "this-file-does-not-exist-9999.txt"
    cit["cross_references"] = refs
    cit_path.write_text(json.dumps(cit), encoding="utf-8")
    payload, code = vmod.validate_manifest(root, "research/research-manifest.json")
    assert code == 1
    assert any("cross_reference_missing_file" in e for e in payload["errors"])


def test_validate_duplicate_artifact_ids(vmod, tmp_path: Path):
    root = tmp_path
    (root / "research").mkdir()
    (root / "docs" / "research").mkdir(parents=True)
    for name in (
        "README.md",
        "benchmark-methodology.md",
        "citation-guide.md",
        "experimental-design.md",
        "open-science-principles.md",
        "publication-strategy.md",
        "reproducibility.md",
        "threats-to-validity.md",
    ):
        (root / "docs" / "research" / name).write_text("# x\n", encoding="utf-8")
    (root / "examples" / "research").mkdir(parents=True)
    for name in ("README.md", "run-research-package-check.sh", "sample-experimental-plan.json"):
        (root / "examples" / "research" / name).write_text("{}", encoding="utf-8")
    (root / "benchmarks").mkdir()
    (root / "benchmarks" / "README.md").write_text("# b\n", encoding="utf-8")
    (root / "benchmarks" / "auditability-failures").mkdir()
    (root / "benchmarks" / "auditability-failures" / "README.md").write_text("# a\n", encoding="utf-8")
    (root / "benchmarks" / "auditability-failures" / "run_benchmark.py").write_text("print(1)\n", encoding="utf-8")
    (root / "README.md").write_text("r\n", encoding="utf-8")
    (root / "CITATION.cff").write_text("cff-version: 1.2.0\n", encoding="utf-8")

    def child(kind: str, aid: str):
        base = {
            "artifact_id": aid,
            "cross_references": {
                "benchmark_methodology": "research/benchmark-methodology.json",
                "citation_metadata": "research/citation-metadata.json",
                "experimental_design": "research/experimental-design.json",
                "reproducibility_checklist": "research/reproducibility-checklist.json",
                "research_manifest": "research/research-manifest.json",
                "threats_to_validity": "research/threats-to-validity.json",
            },
            "schema_version": 1,
            "stable_package_urn": "urn:govai:research:package:1",
            "title": kind,
        }
        if kind == "benchmark_methodology":
            base.update(
                {
                    "benchmark_suite_ids": ["suite"],
                    "evaluation_protocol_id": "e",
                    "methodology_version": "1",
                    "primary_metrics": [{"description": "d", "metric_id": "m1", "unit": "u"}],
                    "protocol_steps": [
                        {
                            "description": "d",
                            "order": 1,
                            "step_id": "s1",
                        }
                    ],
                    "referenced_benchmark_paths": [
                        "benchmarks/README.md",
                        "benchmarks/auditability-failures/README.md",
                        "benchmarks/auditability-failures/run_benchmark.py",
                    ],
                }
            )
        elif kind == "reproducibility_checklist":
            base.update(
                {
                    "artifact_retention_policy": "keep logs",
                    "checklist_sections": [
                        {
                            "items": ["a"],
                            "section_id": "sec1",
                            "title": "t",
                        }
                    ],
                    "checklist_version": "1",
                    "environment_pins": [{"description": "d", "pin_id": "p1"}],
                }
            )
        elif kind == "citation_metadata":
            base.update(
                {
                    "bibtex_entry_type": "software",
                    "preferred_citation": {
                        "cff_path": "CITATION.cff",
                        "repository_url": "https://example.invalid",
                        "software_name": "GovAI",
                        "version_field": "1",
                    },
                    "related_identifiers": [{"identifier_id": "i1", "note": "n", "type": "doi"}],
                }
            )
        elif kind == "experimental_design":
            base.update(
                {
                    "analysis_plan_summary": "summary",
                    "documentation_anchor": "docs/research/experimental-design.md",
                    "primary_hypotheses": [{"hypothesis_id": "h1", "statement": "s"}],
                    "preregistration_anchor": "docs/research/experimental-design.md",
                    "study_design": "design",
                }
            )
        elif kind == "threats_to_validity":
            base.update(
                {
                    "documentation_anchor": "docs/research/threats-to-validity.md",
                    "threat_categories": [
                        {
                            "mitigation_doc_path": "docs/research/benchmark-methodology.md",
                            "threat_description": "d",
                            "threat_id": "t1",
                        }
                    ],
                }
            )
        return base

    dup_id = "same-id"
    (root / "research" / "benchmark-methodology.json").write_text(
        json.dumps(child("benchmark_methodology", dup_id)),
        encoding="utf-8",
    )
    (root / "research" / "citation-metadata.json").write_text(
        json.dumps(child("citation_metadata", dup_id)),
        encoding="utf-8",
    )
    (root / "research" / "experimental-design.json").write_text(
        json.dumps(child("experimental_design", "other-id")),
        encoding="utf-8",
    )
    (root / "research" / "reproducibility-checklist.json").write_text(
        json.dumps(child("reproducibility_checklist", "other-id-2")),
        encoding="utf-8",
    )
    (root / "research" / "threats-to-validity.json").write_text(
        json.dumps(child("threats_to_validity", "other-id-3")),
        encoding="utf-8",
    )
    man = {
        "documentation_paths": [f"docs/research/{n}" for n in (
            "README.md",
            "benchmark-methodology.md",
            "citation-guide.md",
            "experimental-design.md",
            "open-science-principles.md",
            "publication-strategy.md",
            "reproducibility.md",
            "threats-to-validity.md",
        )],
        "example_paths": [
            "examples/research/README.md",
            "examples/research/run-research-package-check.sh",
            "examples/research/sample-experimental-plan.json",
        ],
        "issued_at": "2026-05-13T00:00:00Z",
        "manifest_artifact_id": "govai-research-manifest",
        "package_id": "p",
        "package_version": "1.0.0",
        "research_artifacts": {
            "benchmark_methodology": "research/benchmark-methodology.json",
            "citation_metadata": "research/citation-metadata.json",
            "experimental_design": "research/experimental-design.json",
            "reproducibility_checklist": "research/reproducibility-checklist.json",
            "threats_to_validity": "research/threats-to-validity.json",
        },
        "research_readme_path": "README.md",
        "schema_version": 1,
        "stable_package_urn": "urn:govai:research:package:1",
    }
    (root / "research" / "research-manifest.json").write_text(json.dumps(man), encoding="utf-8")
    payload, code = vmod.validate_manifest(root, "research/research-manifest.json")
    assert code == 1
    assert any("duplicate_artifact_id" in e for e in payload["errors"])


def test_subprocess_validate_json_roundtrip():
    r = subprocess.run(
        ["python3", str(REPO_ROOT / "scripts" / "validate_research_manifest.py"), "--json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["ok"] is True


def test_subprocess_research_package_check_json():
    r = subprocess.run(
        ["python3", str(REPO_ROOT / "scripts" / "research_package_check.py"), "--json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    data = json.loads(r.stdout.strip())
    assert data["ok"] is True
