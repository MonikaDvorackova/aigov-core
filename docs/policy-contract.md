# GovAI policy contract

This document defines the **runtime policy layer**: what is configurable from files, what is fixed in code, and how enforcement behaves. Deployment tier resolution (`dev` / `staging` / `prod`) is documented separately in [`env-resolution.md`](env-resolution.md).

## Config surface (`PolicyConfig`)

JSON files: `policy.<env>.json` then `policy.json`, resolved under `AIGOV_POLICY_DIR` or the process working directory, unless `AIGOV_POLICY_FILE` points at a single file. See `rust/src/policy_config.rs`.

| Field | Type | Default (if omitted) | Meaning |
|-------|------|----------------------|---------|
| `require_approval` | bool | `true` | `model_promoted` must reference a prior `human_approved` event (`approved_human_event_id`) with matching linkage. |
| `block_if_missing_evidence` | bool | `true` | When true, `model_trained` requires a prior `data_registered` for the same `run_id` (ordering in the ledger). |
| `require_passed_evaluation_for_promotion` | bool | `true` | `model_promoted` requires a prior `evaluation_reported` with `passed=true` for the same `run_id`. |
| `require_risk_review_for_approval` | bool | `true` | `human_approved` requires a prior matching `risk_reviewed` with `decision=approve` (same linkage fields as in code). |
| `require_risk_review_for_promotion` | bool | `true` | `model_promoted` requires a prior matching `risk_reviewed` with `decision=approve`. |
| `enforce_approver_allowlist` | bool | `true` | `human_approved` approver must appear in the **effective** allowlist (below). |
| `approver_allowlist` | string array | `["compliance_officer","risk_officer"]` | Allowed approver identifiers. Loaded values are trimmed, lowercased, de-duplicated in order. Must be non-empty when `enforce_approver_allowlist` is `true`. |

**Invalid or missing policy file:**

- **`staging` / `prod`**: startup **fails** (non-zero exit) with **`Invalid policy configuration: refusing to start`** unless a valid file is resolved.
- **`dev`**: fallback to compiled defaults remains **allowed** unless **`AIGOV_POLICY_STRICT=true`** (strict always fails startup on invalid or missing resolved policy).

## Environment override (backward compatible)

- **`AIGOV_APPROVER_ALLOWLIST`**: if set to a non-empty value after trim, it **replaces** `approver_allowlist` from the file for ingest enforcement only. Format: comma-separated names; same trimming, lowercasing, and de-duplication as file entries.

The HTTP **`GET /status`** response includes **`ok`**, **`policy_version`**, and **`environment`** only (see [`api/govai-http-v1.openapi.yaml`](../api/govai-http-v1.openapi.yaml)). Policy knobs and allowlists live in resolved policy files / env at process start (`rust/src/policy_config.rs`), not in this JSON.

## Code invariants (not policy files)

These are **domain and schema rules** enforced in `rust/src/policy.rs`; they are not toggled by `PolicyConfig`:

- **Event types** recognized for structured validation (`data_registered`, `model_trained`, `evaluation_reported`, `risk_*`, `human_approved`, `model_promoted`).
- **Required payload shapes** per event type (field presence and basic types).
- **Enumerations** embedded in messages, e.g. `decision` ∈ {`approve`, `reject`} where applicable; `human_approved.scope` must be `model_promoted` for the promotion workflow.
- **Linkage fields** that tie events together (`assessment_id`, `risk_id`, `dataset_governance_commitment`, `ai_system_id`, `dataset_id`, `model_version_id`, etc.) when a rule requires them.
- **Log scan semantics** for ordering gates: match on `run_id`, event type, and the same linkage fields as implemented in the helper functions (`has_risk_reviewed_approved`, `human_approved_event_ok`, etc.).

Unknown event types are accepted without additional policy checks (pass-through).

## Determinism and audit

- Allowlist matching is **case-insensitive** on approver and allowlist entries.
- Normalized allowlists are stable (trim, lowercase, first-seen de-duplication).
- Effective policy at process start (including source path metadata) is fixed for the lifetime of the process unless you restart with different env/files.

## Release note (summary)

Policy files may declare **`approver_allowlist`** explicitly; defaults match the former hardcoded default list. **`AIGOV_APPROVER_ALLOWLIST`** remains supported as a runtime override for ingest. Invalid combinations (`enforce_approver_allowlist` with an empty allowlist after normalization) fail validation at load and trigger fallback to compile-time defaults. Fine-grained promotion gates use **`require_passed_evaluation_for_promotion`** and **`require_risk_review_for_promotion`** in `rust/src/policy.rs` (no longer tied to `block_if_missing_evidence` for the promotion risk-review step).
