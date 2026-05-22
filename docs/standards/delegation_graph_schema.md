# Delegation Graph Schema

## Purpose

Represent a **directed delegation graph** among humans, agents, and services: who may delegate which `capability_id` to whom, optional expiry, and optional parent delegation for chains. This supports **multi-agent accountability**, **Separation-of-Duties planning**, and **replayable trace** narratives aligned with Phase 4 delegation metadata.

## Canonical fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Required. |
| `graph_id` | string | Required. Stable identifier for this graph document. |
| `tenant_scope` | string | Required. Logical scope label. |
| `nodes` | array | Required, non-empty. |
| `edges` | array | Optional; defaults to empty list if omitted. |

Each **node**:

| Field | Type | Description |
|-------|------|-------------|
| `node_id` | string | Required. Unique in the document. |
| `node_type` | string | Required. One of `HUMAN`, `AGENT`, `SERVICE`. |
| `principal_id` | string | Optional. IAM-style principal when applicable. |
| `agent_id` | string | Optional. Agent identifier when applicable. |

Each **edge**:

| Field | Type | Description |
|-------|------|-------------|
| `delegation_id` | string | Required. Unique in the document. |
| `from_node_id` | string | Required. Must reference a node. |
| `to_node_id` | string | Required. Must reference a node. |
| `capability_id` | string | Required. Delegated capability identifier. |
| `scope` | string | Required. Delegation scope label (opaque string). |
| `expires_at` | string | Optional. Opaque expiry token (for example ISO-8601 string). |
| `parent_delegation_id` | string | Optional. Must reference an existing `delegation_id` when present. |

## Validation rules

- Banned raw content keys are rejected anywhere in the document (see capability policy doc for list).
- `graph_id` and `tenant_scope` are required non-empty strings.
- `nodes` must be non-empty; `node_id` unique; `node_type` constrained.
- `delegation_id` unique across edges.
- Every edge’s `from_node_id` and `to_node_id` must exist in `nodes`.
- `parent_delegation_id`, when set, must match some edge’s `delegation_id`.
- **Cycle detection**: the directed graph formed by edges (`from_node_id` → `to_node_id`) must be acyclic.

## Digest rules

`canonical_digest` over a deterministic preimage:

- `nodes` sorted by `node_id` (with stable field order in each node object).
- `edges` sorted by `delegation_id`.
- Top-level keys sorted in canonical JSON.

## Example JSON

See `examples/standards/delegation_graph.valid.json`.

## CLI usage

```bash
python -m aigov_py.standards.cli validate-delegation-graph path/to/graph.json
python -m aigov_py.standards.cli digest delegation-graph path/to/graph.json
```

## Relationship to GovAI runtime and Phase 4

- Mirrors optional `delegation_context` and `agent_context` fields described for `POST /v1/runtime/evaluate` in Phase 4 documentation, but as a **standalone artefact** for exchange between organizations and tools.
- Does not create or validate a persisted delegation store in the product.

## Non-goals

- No enforcement of delegation at runtime.
- No ledger writes or tenant identity derivation.
- No cryptographic proofs of delegation authenticity in the reference implementation (signing can be layered externally).
