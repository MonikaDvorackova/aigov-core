from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aigov_py.governance_catalog import GovernanceCatalogError, validate_governance_catalog, validate_in_memory


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_catalog_validates() -> None:
    validate_governance_catalog(_repo_root())


def test_mappings_resolve() -> None:
    root = _repo_root()
    controls = _load(root / "docs/governance/controls.v1.yaml")
    reqs = _load(root / "docs/governance/aiact_requirements.v1.yaml")
    mappings = _load(root / "docs/governance/aiact_mappings.v1.yaml")
    reasons = _load(root / "docs/governance/reason_codes.v1.yaml")
    validate_in_memory(controls=controls, requirements=reqs, mappings=mappings, reason_codes=reasons)


def test_reason_codes_resolve() -> None:
    root = _repo_root()
    controls = _load(root / "docs/governance/controls.v1.yaml")
    reqs = _load(root / "docs/governance/aiact_requirements.v1.yaml")
    mappings = _load(root / "docs/governance/aiact_mappings.v1.yaml")
    reasons = _load(root / "docs/governance/reason_codes.v1.yaml")
    validate_in_memory(controls=controls, requirements=reqs, mappings=mappings, reason_codes=reasons)


def test_duplicate_control_ids_fail() -> None:
    root = _repo_root()
    controls = _load(root / "docs/governance/controls.v1.yaml")
    reqs = _load(root / "docs/governance/aiact_requirements.v1.yaml")
    mappings = _load(root / "docs/governance/aiact_mappings.v1.yaml")
    reasons = _load(root / "docs/governance/reason_codes.v1.yaml")

    controls["controls"].append(dict(controls["controls"][0]))
    with pytest.raises(GovernanceCatalogError, match=r"duplicate control_id"):
        validate_in_memory(controls=controls, requirements=reqs, mappings=mappings, reason_codes=reasons)


def test_duplicate_requirement_ids_fail() -> None:
    root = _repo_root()
    controls = _load(root / "docs/governance/controls.v1.yaml")
    reqs = _load(root / "docs/governance/aiact_requirements.v1.yaml")
    mappings = _load(root / "docs/governance/aiact_mappings.v1.yaml")
    reasons = _load(root / "docs/governance/reason_codes.v1.yaml")

    reqs["requirements"].append(dict(reqs["requirements"][0]))
    with pytest.raises(GovernanceCatalogError, match=r"duplicate requirement_id"):
        validate_in_memory(controls=controls, requirements=reqs, mappings=mappings, reason_codes=reasons)


def test_duplicate_reason_codes_fail() -> None:
    root = _repo_root()
    controls = _load(root / "docs/governance/controls.v1.yaml")
    reqs = _load(root / "docs/governance/aiact_requirements.v1.yaml")
    mappings = _load(root / "docs/governance/aiact_mappings.v1.yaml")
    reasons = _load(root / "docs/governance/reason_codes.v1.yaml")

    reasons["reason_codes"].append(dict(reasons["reason_codes"][0]))
    with pytest.raises(GovernanceCatalogError, match=r"duplicate reason_code"):
        validate_in_memory(controls=controls, requirements=reqs, mappings=mappings, reason_codes=reasons)


def test_invalid_mapping_fails() -> None:
    root = _repo_root()
    controls = _load(root / "docs/governance/controls.v1.yaml")
    reqs = _load(root / "docs/governance/aiact_requirements.v1.yaml")
    mappings = _load(root / "docs/governance/aiact_mappings.v1.yaml")
    reasons = _load(root / "docs/governance/reason_codes.v1.yaml")

    mappings["mappings"].append(
        {
            "requirement_id": "AIACT.HRA.ART_999.0",
            "control_id": controls["controls"][0]["control_id"],
            "mapping_strength": "REQUIRED",
            "applicability_risk_classes": ["HIGH"],
            "rationale": "x",
        }
    )
    with pytest.raises(GovernanceCatalogError, match=r"unknown requirement_id"):
        validate_in_memory(controls=controls, requirements=reqs, mappings=mappings, reason_codes=reasons)


def test_invalid_risk_class_fails() -> None:
    root = _repo_root()
    controls = _load(root / "docs/governance/controls.v1.yaml")
    reqs = _load(root / "docs/governance/aiact_requirements.v1.yaml")
    mappings = _load(root / "docs/governance/aiact_mappings.v1.yaml")
    reasons = _load(root / "docs/governance/reason_codes.v1.yaml")

    mappings["mappings"][0]["applicability_risk_classes"] = ["HIGH", "ULTRA"]
    with pytest.raises(GovernanceCatalogError, match=r"invalid risk class"):
        validate_in_memory(controls=controls, requirements=reqs, mappings=mappings, reason_codes=reasons)

