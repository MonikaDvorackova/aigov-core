# Trace Verification Plan Schema

## Purpose

Capture a **structured verification plan** for a multi-step or multi-agent trace: requirements, per-requirement findings, and a deterministic `plan_digest` binding the plan content. This is a **governance and audit planning** artefact, not a cryptographic verifier.

## Canonical fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Required. |
| `trace_id` | string | Required. Identifier for the trace under review. |
| `tenant_scope` | string | Required. Logical scope label. |
| `requirements` | array | Optional; defaults to empty. Each item has `requirement_id` (required) and `description` (string, may be empty). |
| `findings` | array | Optional; defaults to empty. Each item has `finding_id`, `requirement_id`, `status`. |
| `plan_digest` | string | Optional. If present, must equal the canonical digest of the plan fields (excluding `plan_digest` itself). |

**`status`** on each finding must be one of: `PASS`, `WARN`, `FAIL`, `NOT_APPLICABLE`.

## Validation rules

- Raw content field names are rejected project-wide.
- `requirement_id` values must be unique; `finding_id` values must be unique.
- Each finding’s `requirement_id` must reference an existing requirement.
- When `plan_digest` is provided, it must match `digest_trace_verification_plan_document` over the parsed document fields (excluding the digest field from the preimage).

## Digest rules

The digest preimage includes `schema_version`, `tenant_scope`, `trace_id`, sorted `requirements` (by `requirement_id`), and sorted `findings` (by `finding_id`). The digest does **not** embed raw prompts, payloads, or transcript text.

## Example JSON

See `examples/standards/trace_verification_plan.valid.json`.

## CLI usage

```bash
python -m aigov_py.standards.cli validate-trace-verification-plan path/to/plan.json
python -m aigov_py.standards.cli digest trace-verification-plan path/to/plan.json
```

## Relationship to GovAI runtime and Phase 4

- Complements Phase 4 **multi-agent trace export planning** (`multi_agent_traceability.md`, Python `aigov_py.multi_agent_trace`) by describing how an external reviewer would record verification outcomes against explicit requirement IDs.
- Does not evaluate runtime governance or change compliance summary behaviour.

## Non-goals

- No signature verification, chain-of-custody proofs, or replay of raw model inputs/outputs.
- No claim that `PASS` implies legal compliance.
