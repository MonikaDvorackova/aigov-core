from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Final

# Repository-relative schema paths (stable for external implementers).
_REPO_SCHEMAS: Final[tuple[str, ...]] = (
    "schemas/governance-evidence-pack.schema.json",
    "schemas/governance-policy-module.schema.json",
    "schemas/governance-decision-trace.schema.json",
    "schemas/delegation-graph.schema.json",
    "schemas/capability-policy.schema.json",
    "schemas/trace-verification-plan.schema.json",
)


@dataclass(frozen=True)
class RegisteredArtifact:
    """One versioned interchange artefact in the GovAI governance standards registry."""

    artifact_type: str
    """Logical type id (snake_case), used in tooling and conformance reports."""

    schema_version: str
    """Exact schema_version string producers must write for this revision."""

    schema_path: str
    """Path to the JSON Schema file, relative to the repository root."""

    description: str


# Explicit, versioned registry. Add new rows for new interchange revisions; do not mutate rows in place.
GOVERNANCE_STANDARDS_REGISTRY: tuple[RegisteredArtifact, ...] = (
    RegisteredArtifact(
        artifact_type="governance_evidence_pack",
        schema_version="govai.standards.governance_evidence_pack.v1",
        schema_path="schemas/governance-evidence-pack.schema.json",
        description="Portable bundle of governed artifact references with digest manifest and pack digest.",
    ),
    RegisteredArtifact(
        artifact_type="governance_policy_module",
        schema_version="govai.standards.governance_policy_module.v1",
        schema_path="schemas/governance-policy-module.schema.json",
        description="JSON interchange for policy requirements and required evidence codes (distinct from YAML policy modules in pipelines).",
    ),
    RegisteredArtifact(
        artifact_type="governance_decision_trace",
        schema_version="govai.standards.governance_decision_trace.v1",
        schema_path="schemas/governance-decision-trace.schema.json",
        description="Portable record of gate observables with a recorded verdict checked against authoritative recomputation.",
    ),
    RegisteredArtifact(
        artifact_type="delegation_graph",
        schema_version="govai.standards.delegation_graph.v1",
        schema_path="schemas/delegation-graph.schema.json",
        description="Portable delegation graph of principals, agents, and scoped capability edges.",
    ),
    RegisteredArtifact(
        artifact_type="capability_policy",
        schema_version="govai.standards.capability_policy.v1",
        schema_path="schemas/capability-policy.schema.json",
        description="Portable capability definitions with risk class, tool allowlists, and evidence requirements.",
    ),
    RegisteredArtifact(
        artifact_type="trace_verification_plan",
        schema_version="govai.standards.trace_verification_plan.v1",
        schema_path="schemas/trace-verification-plan.schema.json",
        description="Portable trace verification plan with requirements and recorded findings.",
    ),
)


def registry_index_by_schema_version() -> dict[str, RegisteredArtifact]:
    out: dict[str, RegisteredArtifact] = {}
    for row in GOVERNANCE_STANDARDS_REGISTRY:
        if row.schema_version in out:
            raise RuntimeError(f"duplicate schema_version in registry: {row.schema_version}")
        out[row.schema_version] = row
    return out


def resolve_registered(schema_version: str) -> RegisteredArtifact | None:
    return registry_index_by_schema_version().get(schema_version.strip() if isinstance(schema_version, str) else "")


def schema_files_relative() -> tuple[str, ...]:
    return _REPO_SCHEMAS


def validator_for_schema_version(schema_version: str) -> Callable[[Any], Any] | None:
    """Return the Python validator function for a registered schema_version, if any."""
    from aigov_py.standards.capability_policy import validate_capability_policy_document
    from aigov_py.standards.decision_trace import validate_governance_decision_trace_document
    from aigov_py.standards.delegation_graph import validate_delegation_graph_document
    from aigov_py.standards.evidence_pack import validate_governance_evidence_pack_document
    from aigov_py.standards.policy_module import validate_governance_policy_module_document
    from aigov_py.standards.trace_verification import validate_trace_verification_plan_document

    v = (schema_version or "").strip()
    if v == "govai.standards.governance_evidence_pack.v1":
        return validate_governance_evidence_pack_document
    if v == "govai.standards.governance_policy_module.v1":
        return validate_governance_policy_module_document
    if v == "govai.standards.governance_decision_trace.v1":
        return validate_governance_decision_trace_document
    if v == "govai.standards.delegation_graph.v1":
        return validate_delegation_graph_document
    if v == "govai.standards.capability_policy.v1":
        return validate_capability_policy_document
    if v == "govai.standards.trace_verification_plan.v1":
        return validate_trace_verification_plan_document
    return None


def repo_root_from_here() -> Path:
    """python/aigov_py/standards/registry.py -> repo root."""
    return Path(__file__).resolve().parents[3]
