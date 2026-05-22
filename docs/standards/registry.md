# Governance standards registry

This registry lists **versioned interchange artefacts** supported by GovAI’s portable standards tooling. Each row is **immutable for that `schema_version`**: corrections ship as a new `schema_version` string and new schema file where applicable.

| `artifact_type` | `schema_version` | JSON Schema (repo path) | Python validator |
| --- | --- | --- | --- |
| `governance_evidence_pack` | `govai.standards.governance_evidence_pack.v1` | `schemas/governance-evidence-pack.schema.json` | `aigov_py.standards.evidence_pack.validate_governance_evidence_pack_document` |
| `governance_policy_module` | `govai.standards.governance_policy_module.v1` | `schemas/governance-policy-module.schema.json` | `aigov_py.standards.policy_module.validate_governance_policy_module_document` |
| `governance_decision_trace` | `govai.standards.governance_decision_trace.v1` | `schemas/governance-decision-trace.schema.json` | `aigov_py.standards.decision_trace.validate_governance_decision_trace_document` |

## Machine-readable source of truth

The canonical registry table is duplicated in code as `GOVERNANCE_STANDARDS_REGISTRY` in `python/aigov_py/standards/registry.py` so CI and scripts can resolve `schema_version` → validator binding **without** network access.

## Related artefacts (Phase 5 family)

Capability policies, delegation graphs, and trace verification plans remain first-class standards documents with their own `schema_version` prefixes (`govai.standards.capability_policy.v1`, and so on). They are documented under `docs/standards/README.md` and validated by the existing `python -m aigov_py.standards.cli` commands. This Phase 9 registry focuses on **governance pack / policy / decision trace** interchange for external implementers who need a compact, explicit surface.
