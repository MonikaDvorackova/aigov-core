# Governance Evidence Pack Standard

## Purpose

Describe a **portable evidence pack manifest**: a set of artifact references (by `artifact_id` and `content_digest`), a deterministic digest manifest, and an optional `run_id` tying the pack to a GovAI evidence run. This supports **AI Act–oriented evidence packaging**, **CI artefact binding narratives**, and **cross-vendor exchange** without embedding binary payloads in JSON.

**CI and hosted gates:** Customer CI typically materializes `evidence_digest_manifest.json` plus `<run_id>.json`, submits events with `govai submit-evidence-pack`, then verifies digests against `GET /bundle-hash` with `govai verify-evidence-pack` ([github-action.md](../github-action.md)). This standard describes the **portable pack JSON** validators; the **`govai evidence-pack init`** CLI scaffolds a minimal customer pack layout—see [cli-reference.md](../cli-reference.md).

```docs
preset: export-flow
```

## Canonical fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Required. |
| `pack_id` | string | Required. |
| `tenant_scope` | string | Required. |
| `run_id` | string | Optional. Correlates with GovAI `run_id` when used together. |
| `artifacts` | array | Required, non-empty. |
| `digest_manifest` | object | Required. See below. |
| `pack_digest` | string | Optional. If present, must match canonical digest of the pack preimage (excluding `pack_digest`). |

Each **artifact**:

| Field | Type | Description |
|-------|------|-------------|
| `artifact_id` | string | Required. Unique in the pack. |
| `artifact_type` | string | Required. Opaque type label (for example `capability_policy`). |
| `uri` | string | Optional. Retrieval hint only; validators do not fetch. |
| `content_digest` | string | Required. `sha256:` + 64 hex or 64 hex digits (normalized internally). |
| `evidence_type` | string | Required. `GOVERNED` or `REFERENCE`. |
| `control_refs` | array of string | Required for `GOVERNED`: must be non-empty. May be empty for `REFERENCE`. |
| `ai_act_refs` | array of string | Optional; entries must be non-empty strings when present. |

**`digest_manifest`**:

```json
{
  "entries": [
    { "artifact_id": "...", "content_digest": "sha256:..." }
  ]
}
```

Entries must match the **canonical manifest** derived from `artifacts` (same pairs, sorted by `artifact_id`).

## Validation rules

- Banned raw content keys are rejected.
- `artifact_id` unique; `content_digest` must be a valid digest token.
- `GOVERNED` artifacts must have non-empty `control_refs`.
- `digest_manifest` must be **exactly** the canonical manifest implied by `artifacts` (sorting and digest normalization), ensuring deterministic manifests.
- When `pack_digest` is set, it must match the digest of the pack preimage (excluding `pack_digest`).

## Digest rules

- `digest_manifest` canonical form sorts entries by `(artifact_id, content_digest)`.
- `pack_digest` is `canonical_digest` over the pack preimage including canonical `digest_manifest` and sorted `artifacts` (by `artifact_id`).

## Example JSON

See `examples/standards/governance_evidence_pack.valid.json`.

## CLI usage

```bash
python -m aigov_py.standards.cli validate-evidence-pack path/to/pack.json
python -m aigov_py.standards.cli digest evidence-pack path/to/pack.json
```

## Relationship to GovAI runtime and Phase 4

- Aligns with digest-first patterns used elsewhere in GovAI (for example artefact-bound CI flows and Phase 4 signing envelope planning) but **does not** write to the ledger or change export APIs.
- `run_id` is optional metadata for correlation with `GET /compliance-summary` and exports when operators choose to link them.

## Non-goals

- No embedding of evidence file bytes or transcripts.
- No verification that `content_digest` matches external bytes (operators use separate tooling).
- No Stripe, billing, or tenant identity changes.
