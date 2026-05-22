# Runtime governance integration (planning model)

Phase 3 M6 introduces a **standalone integration foundation** that connects governance primitives **conceptually** for a single runtime decision: **controls**, **reason codes**, **dataset lineage**, **human override references**, and **AI Act requirement identifiers**. This layer is **pure data + validation + summarization** — it does **not** wire runtime enforcement, change API behavior, or persist anything.

## Scope

- **In scope**: `RuntimeControlStatus`, `RuntimeRiskClass`, `RuntimeGovernanceVerdict`, `RuntimeControlEvaluation`, `DatasetLineageRef`, `HumanOverrideRef`, `RuntimeGovernanceContext`, `RuntimeGovernanceSummary`, `validate_runtime_governance_context`, `summarize_runtime_governance`, and digest validation helpers (`is_valid_digest_token`).
- **Out of scope**: runtime enforcement wiring, HTTP `/evaluate` (or similar) response shape changes, database migrations, ledger writes, compliance-summary changes, production enforcement, and embedding **raw user content** (only opaque ids, digests, and refs).

## Purpose

The types model how a **runtime decision** (identified by `runtime_decision_id` and `correlation_id`) ties to:

| Link | Representation |
|------|----------------|
| Controls | `control_evaluations` with `PASS` / `FAIL` / `NOT_APPLICABLE`, each with `reason_codes` and `evidence_refs` |
| Reason codes | Opaque strings in `reason_codes` per control (required when status is `FAIL`) |
| Dataset lineage | Optional `dataset_lineage_refs` with `dataset_id` + `dataset_digest` |
| Human override | HTTP **`override_ref`** (M7.4): `override_id` + `target_decision_id`; same semantics as library `HumanOverrideRef` / `human_override_ref` in the planning model |
| AI Act requirements | Optional `ai_act_requirement_refs` (opaque requirement identifiers) |

`tenant_id`, `artifact_digest`, `policy_bundle_version`, and `risk_class` anchor the decision in tenant policy and artifact identity.

## Required fields and validation

1. **`runtime_decision_id`**, **`correlation_id`**, **`tenant_id`**, **`policy_bundle_version`** — non-empty after stripping.
2. **`artifact_digest`** — exactly **64 hex digits** or **`sha256:`** followed by **64 hex digits** (hex case-insensitive for validation).
3. **`risk_class`** — must be a **`RuntimeRiskClass`** enum member: `MINIMAL`, `LIMITED`, `HIGH`, `PROHIBITED`.
4. **Each control evaluation** — non-empty `control_id` (after strip); if `status` is **`FAIL`**, at least one **non-empty** `reason_codes` entry after stripping.
5. **Dataset lineage** (if any ref is present) — each ref needs non-empty `dataset_id` and a digest matching the same artifact digest rules.
6. **Override** (if present) — non-empty `override_id`; **`target_decision_id`** must equal **`runtime_decision_id`** (after strip).
7. **`ai_act_requirement_refs`** — every element non-empty after stripping if the tuple is used.

`validate_runtime_governance_context` returns a **sorted, deduplicated** tuple of stable error strings (deterministic ordering).

## Summary verdict (`summarize_runtime_governance`)

Deterministic rules (in order):

1. **Any control with `FAIL`** → verdict **`INVALID`**, with **`failing_control_ids`** sorted by `(control_id, evaluation_index)` for stable ordering.
2. **No `FAIL`**, but validation errors remain → **`BLOCKED`**.
3. **No `FAIL`** and **valid context** → **`VALID`** when all evaluated controls are **`PASS`** or **`NOT_APPLICABLE`** (no `FAIL`).

`NOT_APPLICABLE` does **not** by itself produce `INVALID` or `BLOCKED`; it is treated as non-blocking relative to pass/fail semantics.

## Fail-safe behavior and determinism

No filesystem, network, or DB access. Repeated calls with equal inputs yield equal `RuntimeGovernanceSummary` values.

## Future wiring

Future work will map **runtime evaluate responses** into `RuntimeGovernanceContext` / `RuntimeGovernanceSummary`, map **reason codes** to **controls** and **AI Act requirements** in policy, and optionally persist audit artifacts — **none of that is implemented in M6**.

## Phase 3 M7.1 note: runtime evaluate response enrichment (additive only)

Phase 3 M7.1 extends `POST /v1/runtime/evaluate` with **additive response enrichment fields** that expose placeholder runtime governance metadata needed for future wiring:

- `schema_version` = `runtime.evaluate.response.v1`
- `governance_context_version` = `runtime.governance.context.v1`
- `control_evaluations` — M7.2: one stub evaluation per mode (see below); was `[]` under M7.1 only
- `dataset_lineage_refs` — M7.3: optional request field; validated `dataset_id` + `dataset_digest` objects are echoed here and in the ledger `governance_enrichment` (omitted/`null` ⇒ `[]`)
- `override_ref` — M7.4: optional request object; validated `override_id` + `target_decision_id` echoed here and in the ledger `governance_enrichment` (omitted/`null` ⇒ `null`)

## Phase 3 M7.3 note: dataset lineage attachment (shadow metadata only)

Phase 3 **M7.3** accepts an optional `dataset_lineage_refs` array on `POST /v1/runtime/evaluate`. Each entry carries **only** `dataset_id` and `dataset_digest` (same SHA-256 digest token rules as artifact digests). Invalid lineage input returns **400** with `VALIDATION_ERROR` and does not affect verdict semantics for requests that pass validation.

Before **M7.8**, lineage was metadata-only (`enforcement` was a legacy **`none`** placeholder). With **Phase 3 M7.8** shipped:

- **`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT=off`**: lineage rule rows are **not** merged (`risk_class` is ignored); core **`disabled`/`shadow`** verdicts stay authoritative.
- **`shadow`/`enforced`**: **`HIGH`** + empty lineage merges a **`dataset_lineage_required`** sentinel into **`governance_summary`** (**`WARN`** vs **`FAIL`** determines summary verdict; **`enforced`** + tenant allowlist can elevate top-level **`verdict`** per **`runtime_enforcement_gate.md`**).

Lineage still does **not** feed **`GET /compliance-summary`** or general policy ingestion.

## Phase 3 M7.4 note: human override reference (shadow metadata only)

Phase 3 **M7.4** accepts an optional `override_ref` object on `POST /v1/runtime/evaluate` with **`override_id`** and **`target_decision_id`** (both non-empty after trim). The target must match this response’s **`decision_id`** **or** the correlation-derived runtime run id (`runtime_<correlation_id>`). Omitted or **`null`** ⇒ **`null`** in the HTTP body and in `payload.governance_enrichment.override_ref`. Invalid `override_ref` returns **400** with `VALIDATION_ERROR`.

**M7.4 does not authorize bypass** — attached override metadata is **observability only** and does **not** by itself convert `BLOCKED`/`INVALID` into `VALID`. **RBAC / separation-of-duties** approval wiring for overrides remains future work (**M7.6+** scopes), regardless of **`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT`**.

- `ai_act_requirement_refs` = `[]`
- `policy_bundle_version` = active policy version (or deployment `policy_version` fallback)
- `enforcement` = **`off`/`shadow`/`enforced`** (resolved from **`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT`** with legacy **`none`** removed)

M7.1 introduced the enrichment shell; Phase 3 **M7.2** fills `control_evaluations` with a **minimal structured reason-code-to-control mapping** only (additive). Mappings (`source: runtime_mode`):

| Stub reason | `control_id` | `status` |
|-------------|--------------|----------|
| `runtime_not_enabled` | `GOVAI.RUNTIME.MODE_DISABLED` | `FAIL` |
| `shadow_mode_no_enforcement` | `GOVAI.RUNTIME.SHADOW_MODE` | `WARN` |

**Stub `control_evaluations[*]`** remain **backward compatible** (**single runtime-mode row**). Derived governance rows (lineage warnings, sentinel mapping **`FAIL`**s, malformed-context probes) ride inside **`governance_summary.control_evaluations[]`** alongside ledger **`governance_enrichment.governance_summary`**.

## Phase 3 M7.8 note: opt-in governance enforcement + `risk_class`

Phase 3 **M7.8** extends `POST /v1/runtime/evaluate` without touching compliance-summary or tenant derivation:

| Field / env | Notes |
|-------------|-------|
| `GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT` | Determines how governance overlays behave: **`shadow`** never mutates top-level **`verdict`**. **`off`** keeps legacy **`GOVAI_RUNTIME_EVALUATE`** disabled/shadow preview semantics authoritative for **`verdict`**. **`enforced`** may escalate **`BLOCKED`/`INVALID`** for allowlisted tenants when governance fails. |
| `GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT_TENANTS` | Comma-separated allowlist (trimmed IDs). Mandatory for **`enforced`** tenancy gating — absence keeps enforcement non-blocking (**`shadow`** response hint). Tenants derive from authenticated API-key mapping (**never arbitrary headers alone**). |
| `risk_class` (`MINIMAL`\|`LIMITED`\|`HIGH`\|`PROHIBITED`) | Defaults to **`LIMITED`**. **`HIGH`** with empty lineage ⇒ **`WARN`** sentinel in **`shadow`**, **`BLOCKED`** (**`dataset_lineage_required`**) under allowlisted **`enforced`**. |
| `governance_summary` object | Mirrors ledger **`governance_enrichment.governance_summary`**: aggregates verdict, deterministic reason_codes, richer control evaluations, lineage refs echo, **`override_ref`**, risk class snapshot, **`enforcement_mode`**, **`enforced`**. |

Operational introspection on **`GET /ready`** and **`GET /status`** echoes **`runtime_governance_enforcement`** so deployers confirm **mode / allowlist / enforceable**.
