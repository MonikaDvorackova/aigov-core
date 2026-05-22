# GovAI ecosystem standards (Phase 5)

This directory describes **machine-readable standards** for interoperability around GovAI’s decision-centric governance model. Implementations live in Python under `aigov_py.standards` (validators, canonical digests, and a standalone CLI).

## Documents

| Standard | Specification | Example |
|----------|---------------|---------|
| Open Capability Policy | [capability_policy_schema.md](capability_policy_schema.md) | `examples/standards/capability_policy.valid.json` |
| Delegation Graph | [delegation_graph_schema.md](delegation_graph_schema.md) | `examples/standards/delegation_graph.valid.json` |
| Trace Verification Plan | [trace_verification_plan_schema.md](trace_verification_plan_schema.md) | `examples/standards/trace_verification_plan.valid.json` |
| Governance Evidence Pack | [governance_evidence_pack_standard.md](governance_evidence_pack_standard.md) | `examples/standards/governance_evidence_pack.valid.json` |

## ISO/IEC 42001 readiness support

| Topic | Document | Machine-readable |
|-------|----------|------------------|
| Readiness overview | [iso-42001.md](iso-42001.md) | [iso-42001-alignment-manifest.json](iso-42001-alignment-manifest.json) |
| Clause mapping (indicative) | — | [iso-42001-clause-index.json](iso-42001-clause-index.json) |

Validators: `make iso-42001-readiness-check` (not certification or legal compliance).

## Phase 9 — Registry interchange (explicit `schema_version` rows)

| Topic | Document | Example JSON |
|-------|----------|--------------|
| Interchange spec | [interchange-specification.md](interchange-specification.md) | `examples/standards/evidence-pack.valid.json`, `policy-module.valid.json`, `decision-trace.valid.json` |
| Registry table | [registry.md](registry.md) | — |
| Conformance CLI / JSON output | [conformance.md](conformance.md) | `scripts/validate_standard_conformance.py` |

## CLI (standalone and `govai`)

From the `python/` directory (editable install or `PYTHONPATH=.`):

```bash
python -m aigov_py.standards.cli validate-capability-policy ../examples/standards/capability_policy.valid.json
python -m aigov_py.standards.cli validate-delegation-graph ../examples/standards/delegation_graph.valid.json
python -m aigov_py.standards.cli validate-trace-verification-plan ../examples/standards/trace_verification_plan.valid.json
python -m aigov_py.standards.cli validate-evidence-pack ../examples/standards/governance_evidence_pack.valid.json
python -m aigov_py.standards.cli digest capability-policy ../examples/standards/capability_policy.valid.json
```

Top-level **`govai`** (same commands, same deterministic JSON on stdout):

```bash
govai standards validate-capability-policy ../examples/standards/capability_policy.valid.json
```

JSON is the canonical on-disk format; YAML is accepted when PyYAML is installed.

## ISO/IEC 42001 readiness (documentation)

| Topic | Document |
|-------|----------|
| AIMS alignment framing (not certification) | [iso-42001-readiness.md](iso-42001-readiness.md) |

## Further reading

| Topic | Document |
|-------|----------|
| Threat model (standards tooling) | [threat-model.md](threat-model.md) |
| Correctness & limits | [correctness.md](correctness.md) |
| Evaluation harness | [evaluation.md](evaluation.md) |
| Registry conformance | [conformance.md](conformance.md) |
| Implementer checklist | [implementer-checklist.md](implementer-checklist.md) |

## Relationship to the product

These standards are **sidecar artefacts**: they do not change runtime enforcement, persistence, ledger semantics, or `GET /compliance-summary`. They are intended for ecosystem exchange (policy bundles, delegation graphs, verification plans, evidence pack manifests) and for alignment with Phase 4 multi-agent planning (`docs/governance/phase4_multi_agent_governance.md`).

Strategic context: `docs/governance/phase5_research_and_ecosystem.md`.

Implementation report: `docs/reports/repo-debt-audit-and-cleanup.md`.
