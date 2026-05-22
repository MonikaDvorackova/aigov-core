# Strong Core Contract Note

## Canonical identifiers

The strong core uses explicit canonical identifiers across events, bundle, projection, and summary:

- `ai_system_id`
- `dataset_id`
- `model_version_id`
- `risk_ids` (full source of truth for risk identity set)
- `primary_risk_id` (optional convenience pointer derived from `risk_ids`; not a replacement for `risk_ids`)

For risk identity, `risk_ids` is authoritative. `primary_risk_id` is only a compact pointer for consumers that need a single representative risk.

In bundle and projections, membership in `risk_ids` is derived only from risk lifecycle events (`risk_recorded`, `risk_mitigated`, `risk_reviewed`), not from linkage fields on other event types.

## Compliance summary contract

`GET /compliance-summary` returns `ok`, `schema_version` (`aigov.compliance_summary.v2`), `policy_version`, `run_id`, and `current_state` embedding the projection below (on load failure: `ok: false`, `schema_version`, `error`, `policy_version`, `run_id`).

`ComplianceCurrentState` is a domain-oriented contract (`aigov.compliance_current_state.v2`) with these sections:

- `identifiers`
- `system`
- `dataset`
- `model`
- `risks`
- `approval`
- `evidence`

This keeps the core regulation agnostic. Legal or article-specific mapping belongs in a separate presentation/formatting layer.

## Source-of-truth chain

The data chain is intentionally linear:

1. immutable ledger (`/evidence` events in append-only log)
2. bundle document (`/bundle`, canonicalized and hashable)
3. projection (`ComplianceCurrentState` derivation from events + context)
4. compliance summary (`/compliance-summary` API response contract)

## Current limitation

- `evidence.bundle_hash` is available in summary and derived from the canonical bundle hash.
- `evidence.bundle_generated_at` is currently `null` in summary because bundle generation time is not emitted in immutable ledger events and is not persisted in the current core summary path.

## Enterprise workflow (`compliance_workflow`) — override only

The Postgres **`compliance_workflow`** table and **`/api/compliance-workflow*`** routes provide a **team-scoped queue** (register, approve/reject, promotion allow/block). They **do not** append to the ledger, replace **`policy.rs`**, or define a second compliance projection.

**Authoritative readiness** for “can this run be promoted?” is always:

`immutable ledger` → `bundle` → `projection` → **`GET /compliance-summary`** (`current_state`).

Workflow state may **block or allow operationally** inside a product (e.g. internal sign-off) but must be **reconciled** with the summary; API responses include **`decision_authority`** on successful workflow calls to make this explicit.

## Repo packaging note

The contracts above describe the **semantic core**. What is treated as open-source “core” vs. optional product surfaces for v0.1 is summarized in [`OPEN_SOURCE_SCOPE.md`](../OPEN_SOURCE_SCOPE.md) (no repo split).
