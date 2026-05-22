from __future__ import annotations

from importlib import import_module
from typing import Any

from .common import (
    StandardsLoadError,
    ValidationIssue,
    ValidationResult,
    canonical_digest,
    canonical_json,
    load_standard_document,
    normalize_digest_token,
    validate_digest_token,
)

# NOTE:
# This package intentionally keeps imports of individual standards modules *lazy*.
# The common utilities must be importable independently while Phase 5 modules evolve.
# Accessing a missing standard symbol will raise ModuleNotFoundError at attribute access time
# (not at package import time), and any real import error inside an existing module will
# propagate without being masked.

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    # capability_policy
    "canonical_capability_policy_document": ("aigov_py.standards.capability_policy", "canonical_capability_policy_document"),
    "digest_capability_policy_document": ("aigov_py.standards.capability_policy", "digest_capability_policy_document"),
    "validate_capability_policy_document": ("aigov_py.standards.capability_policy", "validate_capability_policy_document"),
    # delegation_graph
    "canonical_delegation_graph_document": ("aigov_py.standards.delegation_graph", "canonical_delegation_graph_document"),
    "digest_delegation_graph_document": ("aigov_py.standards.delegation_graph", "digest_delegation_graph_document"),
    "validate_delegation_graph_document": ("aigov_py.standards.delegation_graph", "validate_delegation_graph_document"),
    # trace_verification
    "canonical_trace_verification_plan_document": ("aigov_py.standards.trace_verification", "canonical_trace_verification_plan_document"),
    "digest_trace_verification_plan_document": ("aigov_py.standards.trace_verification", "digest_trace_verification_plan_document"),
    "validate_trace_verification_plan_document": ("aigov_py.standards.trace_verification", "validate_trace_verification_plan_document"),
    # evidence_pack
    "canonical_governance_evidence_pack_document": ("aigov_py.standards.evidence_pack", "canonical_governance_evidence_pack_document"),
    "digest_governance_evidence_pack_document": ("aigov_py.standards.evidence_pack", "digest_governance_evidence_pack_document"),
    "validate_governance_evidence_pack_document": ("aigov_py.standards.evidence_pack", "validate_governance_evidence_pack_document"),
    # policy_module (JSON interchange)
    "canonical_governance_policy_module_document": ("aigov_py.standards.policy_module", "canonical_governance_policy_module_document"),
    "digest_governance_policy_module_document": ("aigov_py.standards.policy_module", "digest_governance_policy_module_document"),
    "validate_governance_policy_module_document": ("aigov_py.standards.policy_module", "validate_governance_policy_module_document"),
    # decision_trace
    "canonical_governance_decision_trace_document": ("aigov_py.standards.decision_trace", "canonical_governance_decision_trace_document"),
    "digest_governance_decision_trace_document": ("aigov_py.standards.decision_trace", "digest_governance_decision_trace_document"),
    "validate_governance_decision_trace_document": ("aigov_py.standards.decision_trace", "validate_governance_decision_trace_document"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attr = target
    mod = import_module(module_name)
    return getattr(mod, attr)


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_LAZY_EXPORTS.keys()))

__all__ = [
    "StandardsLoadError",
    "ValidationIssue",
    "ValidationResult",
    "canonical_json",
    "canonical_digest",
    "validate_digest_token",
    "normalize_digest_token",
    "load_standard_document",
    "canonical_capability_policy_document",
    "digest_capability_policy_document",
    "validate_capability_policy_document",
    "canonical_delegation_graph_document",
    "digest_delegation_graph_document",
    "validate_delegation_graph_document",
    "canonical_trace_verification_plan_document",
    "digest_trace_verification_plan_document",
    "validate_trace_verification_plan_document",
    "canonical_governance_evidence_pack_document",
    "digest_governance_evidence_pack_document",
    "validate_governance_evidence_pack_document",
    "canonical_governance_policy_module_document",
    "digest_governance_policy_module_document",
    "validate_governance_policy_module_document",
    "canonical_governance_decision_trace_document",
    "digest_governance_decision_trace_document",
    "validate_governance_decision_trace_document",
]

