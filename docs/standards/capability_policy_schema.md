# Open Capability Policy Schema

## Purpose

Define a portable, versioned **capability policy** for AI systems and agents: which `capability_id` values exist, their risk class, which tools are allowed, structural constraints, and which evidence references must exist before a deployment or runtime decision can be treated as governed. This supports **MCP and tool taxonomies**, **separation-of-duties style constraints**, and **AI Act evidence references** without embedding prompts or payloads.

## Canonical fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Required. Version tag for this document shape. |
| `policy_id` | string | Required. Stable identifier for the policy document. |
| `tenant_scope` | string | Required. Logical scope label (not a GovAI ledger tenant override). |
| `capabilities` | array | Required, non-empty. List of capability definitions. |

Each element of `capabilities`:

| Field | Type | Description |
|-------|------|-------------|
| `capability_id` | string | Required. Unique within the document. |
| `name` | string | Required. Short title. |
| `description` | string | Required. Human-oriented summary (not a prompt log). |
| `risk_class` | string | Required. One of `MINIMAL`, `LIMITED`, `HIGH`, `PROHIBITED`. |
| `allowed_tools` | array of string | Required, non-empty. Tool identifiers (for example MCP tool names). Unique per capability. |
| `constraints` | array of object | Optional. Each object has `constraint_type` (required string) and optional `constraint_ref`. |
| `evidence_requirements` | array of string | Required, non-empty. Evidence reference identifiers (opaque strings). |
| `ai_act_refs` | array of string | Optional. Non-empty strings when present. |

## Validation rules

- Root must be an object; banned raw field names anywhere under the root are rejected (`prompt`, `content`, `raw_payload`, `input_text`, `output_text`, `message_body`).
- `schema_version`, `policy_id`, and `tenant_scope` must be non-empty strings.
- `capabilities` must be a non-empty array; each entry must be an object satisfying the table above.
- `capability_id` values must be unique (duplicates are rejected).
- `risk_class` must be exactly one of the four allowed literals.
- `allowed_tools` must be non-empty; each entry a non-empty string; no duplicates within a capability.
- `evidence_requirements` must be non-empty; each entry a non-empty string.
- `constraints`, when present, must be arrays of objects with valid `constraint_type`.

## Digest rules

The document digest is `canonical_digest(preimage)` where `preimage` is a deterministic JSON object:

- Top-level keys sorted lexicographically in the canonical JSON output.
- `capabilities` sorted by `capability_id`.
- Within each capability, `constraints` sorted by `(constraint_type, constraint_ref)`.
- Lists such as `allowed_tools`, `evidence_requirements`, and `ai_act_refs` appear in **document order** inside each capability object in the canonical preimage (capabilities themselves are sorted by id).

The digest string is always `sha256:` + 64 lowercase hex characters (see `aigov_py.standards.common.canonical_digest`).

## Example JSON

See `examples/standards/capability_policy.valid.json`.

Minimal shape:

```json
{
  "schema_version": "govai.standards.capability_policy.v1",
  "policy_id": "pol.example",
  "tenant_scope": "tenant.example",
  "capabilities": [
    {
      "capability_id": "cap.example",
      "name": "Example",
      "description": "Example capability.",
      "risk_class": "LIMITED",
      "allowed_tools": ["tool_a"],
      "constraints": [],
      "evidence_requirements": ["ev.example"],
      "ai_act_refs": []
    }
  ]
}
```

## CLI usage

```bash
python -m aigov_py.standards.cli validate-capability-policy path/to/policy.json
python -m aigov_py.standards.cli digest capability-policy path/to/policy.json
```

## Relationship to GovAI runtime and Phase 4

- **Phase 4** introduces optional `capability_id` on runtime evaluation metadata and delegation references (`docs/governance/phase4_multi_agent_governance.md`). This schema is a **portable declaration** of what those identifiers mean outside the server.
- The **audit service** continues to own promotion and compliance summary semantics; this standard does not alter `POST /v1/runtime/evaluate` enforcement or `GET /compliance-summary`.

## Non-goals

- No prompt or model output storage.
- No automatic mapping to legal compliance verdicts.
- No network fetch or signature verification in the reference validators.
