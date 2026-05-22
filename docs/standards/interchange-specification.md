# Governance interchange specification

This specification defines **portable JSON artefacts** for exchanging governance metadata between tools, repositories, and audit systems **without** requiring a live GovAI ledger connection. All artefacts:

- declare an exact `schema_version` string registered in `docs/standards/registry.md` (and `python/aigov_py/standards/registry.py`);
- are validated **deterministically** by Python under `python/aigov_py/standards/`;
- ship JSON Schema under `schemas/` for third-party validators;
- reject forbidden raw-content keys anywhere in the tree (see `aigov_py.standards.common.find_raw_content_fields`).

## 1. Governance evidence pack (`governance_evidence_pack`)

**Purpose:** describe a versioned bundle of **artifact references** (with digests) suitable for evidence exchange and offline verification of structural integrity.

**Required fields:**

- `schema_version`: exactly `govai.standards.governance_evidence_pack.v1`.
- `pack_id`, `tenant_scope`: non-empty strings.
- `artifacts`: non-empty array of objects with `artifact_id`, `artifact_type`, `content_digest`, `evidence_type` (`GOVERNED` or `REFERENCE`), `control_refs`, `ai_act_refs`, optional `uri`.
- `digest_manifest.entries`: must match the **canonical manifest** derived from `artifacts` (sorted by `artifact_id`), each entry `{artifact_id, content_digest}`.
- `pack_digest`: must equal the canonical digest over the pack fields (excluding the stored `pack_digest` value itself from the preimage—see `digest_governance_evidence_pack_document`).

**Rules of note:**

- `GOVERNED` artefacts require non-empty `control_refs`.
- Digest tokens are `sha256:<64 lowercase hex>` after normalization.

**Example:** `examples/standards/evidence-pack.valid.json`.

## 2. Governance policy module (`governance_policy_module`)

**Purpose:** JSON interchange for **policy requirement codes** and their **required evidence** strings. This is complementary to YAML policy modules consumed by `aigov_py.policy_loader` in training pipelines: the JSON form is optimized for **repository interchange**, code review, and signing workflows.

**Required fields:**

- `schema_version`: exactly `govai.standards.governance_policy_module.v1`.
- `policy`: `{id, name, version}` non-empty strings.
- `requirements`: non-empty array of `{code, required_evidence}`; `required_evidence` is a non-empty string array; `code` values must be unique.

**Digest:** canonical JSON digest over sorted requirement order (by `code`) and stable key ordering—see `digest_governance_policy_module_document`.

**Example:** `examples/standards/policy-module.valid.json`.

## 3. Governance decision trace (`governance_decision_trace`)

**Purpose:** capture a **closed set of observables** used by the evaluation gate model together with a **recorded** `VALID` / `INVALID` / `BLOCKED` verdict. Conformance requires that `recorded_gate_verdict` equals the verdict returned by `decision_gate_verdict_from_fields` in `aigov_py.experiments.gate_model` for the same `gate_inputs`, preserving **authoritative semantics** without changing runtime services.

**Required fields:**

- `schema_version`: exactly `govai.standards.governance_decision_trace.v1`.
- `trace_id`, `tenant_scope`, `run_id`: non-empty strings.
- `recorded_gate_verdict`: `VALID`, `INVALID`, or `BLOCKED`.
- `gate_inputs`: object whose keys are **exactly** the closed field bundle aligned with `aigov_py.experiments.scenario_fields.make_base_fields` (no unknown keys, no missing keys). Values follow JSON types expected by the gate model (`evaluation_result` is `"pass"` or `"fail"`, booleans for flags, `approval` is a string, and so on).

**Digest:** canonical digest over a stable key ordering of the trace payload—see `digest_governance_decision_trace_document`.

**Example:** `examples/standards/decision-trace.valid.json`.

## Interoperability guidance

1. **Producers** should emit UTF-8 JSON with stable logical content; avoid embedding secrets or raw prompts in interchange documents.
2. **Consumers** should validate with `validate_conformance` or the per-document validators before trusting digests or verdict fields.
3. **Version bumps** require a new `schema_version` const and a new registry row; never silently alter meaning under an existing `schema_version`.
