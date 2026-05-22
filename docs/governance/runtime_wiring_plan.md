# Phase 3 M7 — Runtime wiring plan

This document is an **implementation plan only**. It does not change runtime behavior, APIs, persistence, or compliance-summary. It builds on Phase 3 foundations M1–M6 (control catalog, RBAC, human override, dataset governance, audit export, runtime governance integration model).

**Authoritative integration shape (M6):** `docs/governance/runtime_integration.md` and `python/aigov_py/runtime_governance.py`.

---

## 1. Which components get wired first

Order is driven by **lowest blast radius** and **dependency direction** (opaque ids and digests before policy lookups; shadow data before enforcement).

| Priority | Component | Rationale |
|----------|-----------|-----------|
| 1 | **M6 context builder (library-only)** | Map existing evaluate inputs/outputs into `RuntimeGovernanceContext` without changing HTTP status codes or core verdict fields. |
| 2 | **Reason codes + control catalog (M1)** | Enrichment and validation need stable `control_id` and reason-code vocabulary before lineage/override attach semantics are trustworthy. |
| 3 | **AI Act requirement refs (policy mapping)** | Depends on control + reason vocabulary; stays advisory until explicit gate. |
| 4 | **Dataset lineage (M4)** | Attach after digest/id rules are stable; shadow-only until opt-in. |
| 5 | **Human override refs (M3)** | Requires matching `target_decision_id` to `runtime_decision_id`; follows lineage in shadow stack. |
| 6 | **Audit export manifest planning (M5)** | Consumes completeness model + future manifest of what *would* be exported; no writes. |
| 7 | **RBAC (M2) on future management APIs** | Isolated from hot evaluate path until dedicated management surface exists. |
| 8 | **Production enforcement gate (M7.7)** | Last; explicit product + operator opt-in only. |

---

## 2. What remains read-only

Until **M7.7** explicit opt-in (and even then, limited to agreed scope):

- **Runtime evaluate core semantics:** HTTP contract, default fail-closed behavior, auth expectations, and existing verdict fields used by clients today remain unchanged through **M7.1** as *behaviorally equivalent*; M7.1 may only add **optional, additive** response fields (see §5).
- **`summarize_runtime_governance` / `validate_runtime_governance_context`:** No change to ordering rules, verdict enum meanings, or validation error strings without a dedicated versioning PR.
- **Compliance-summary:** No reads/writes/shape changes in M7.x wiring PRs.
- **Ledger:** No new writes in M7.1–M7.6 (existing `runtime_decision` append remains unchanged; M7.x may only enrich the JSON payload consistently with HTTP responses); M7.7 may introduce writes only if explicitly approved and scoped (out of scope for this plan’s default path — prefer **separate** ledger phase after gate).
- **Database schema:** No migrations in M7.x wiring series; any persistence prototypes use in-memory or fixture-only tests.
- **Audit export execution:** Manifest *planning* only until a later phase; no bulk export jobs triggered from evaluate.

Shadow lineage/override attachments (**M7.3**, **M7.4**) are **validated metadata** that shipped without changing core **`GOVAI_RUNTIME_EVALUATE`** preview defaults. **M7.8 (`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT*`)** is the explicit opt-in that may merge governance overlays — including optional top-level **`verdict`** elevations — only under **`enforced`** with a tenant allowlist (**`shadow`** governance never silently flips previews; **`off`** keeps legacy **`GOVAI_RUNTIME_EVALUATE`** semantics).

---

## 3. Which invariants must not change

| Invariant | Owner | Notes |
|-----------|-------|-------|
| **Determinism** | M6 | Same `RuntimeGovernanceContext` → same `RuntimeGovernanceSummary`; sorted/deduped validation errors. |
| **No raw user content in governance context** | M6 | Only opaque ids, digests, refs; no prompts, payloads, or PII in `RuntimeGovernanceContext`. |
| **`FAIL` → `INVALID`** | M6 | Precedence over `BLOCKED`. |
| **Validation errors without `FAIL` → `BLOCKED`** | M6 | Distinct from `INVALID`. |
| **Digest format** | M6 | 64 hex or `sha256:<64 hex>`. |
| **Override `target_decision_id` == `runtime_decision_id`** | M6 | After strip; enforced at validation. |
| **Tenant isolation** | Runtime + RBAC | RBAC must not weaken tenant boundaries when applied to management APIs. |
| **Default deny (RBAC)** | M2 | Unchanged when wiring authorization. |
| **Existing Rust HTTP tests for `/v1/runtime/evaluate`** | Phase 2 M0+ | Must pass unless a PR explicitly extends contract with **additive** assertions only (M7.1+). |

---

## 4. Exact future PR sequence

Each PR is independently reviewable; merge order is numeric.

| PR | Title | Scope |
|----|-------|-------|
| **M7.1** | Runtime evaluate response enrichment, no enforcement | Add **optional** governance-related fields to evaluate JSON (or parallel `X-` / nested object per API style guide), populated when context is buildable; **must not** change existing verdict/status fields or HTTP error mapping. |
| **M7.2** | Runtime control evaluation mapping (structured stub) | **`/v1/runtime/evaluate` only:** emit `control_evaluations` from existing stub reason codes (`runtime_mode` source). **No** catalog validation, **no** verdict/enforcement change; **no** compliance-summary or DB impact. **M7.7** remains the explicit opt-in gate for production enforcement. |
| **M7.3** | Dataset lineage attachment, shadow only | **M7.3 (implemented):** optional request `dataset_lineage_refs` validated and echoed in HTTP + ledger `governance_enrichment` (metadata only; empty if omitted). Does **not** change verdict or enforcement. **Future:** align with M4 dataset primitives; HIGH-risk lineage enforcement is **M7.7** only. |
| **M7.4** | Override reference attachment, shadow only | **M7.4 (implemented):** optional request `override_ref` (`override_id`, `target_decision_id`) validated and echoed in HTTP + ledger `governance_enrichment` (metadata only; `null` if omitted). Target must match response `decision_id` or `runtime_<correlation_id>`. Does **not** authorize bypass or change verdict/enforcement. **RBAC/SoD** on overrides stays **future (M7.6+)**. |
| **M7.5** | Audit export manifest planning | **Implemented as pure Python helper/model code only:** `python/aigov_py/audit_export_manifest.py` builds deterministic in-memory manifest plans from M5 request/completeness primitives. No export execution, no HTTP/API wiring, no DB, no ledger writes, no immutable package generation. |
| **M7.6** | RBAC enforcement on future management APIs only | **Planning/design only in this bundle:** `docs/governance/rbac_enforcement_plan.md` defines permissions, scope resolution, SoD, failure semantics, audit event requirements, tests, and NO-GO conditions. No RBAC on `/v1/runtime/evaluate`. |
| **M7.7** | Production enforcement gate + design lock | `docs/governance/runtime_enforcement_gate.md` anchors operator NO-GOs; **implementation** ships as **M7.8 Rust wiring** tied to **`POST /v1/runtime/evaluate`**, **`runtime_decision` ledger enrichment**, and **`GET /ready` diagnostics. |

---

## 5. Runtime evaluate integration strategy

- **Phase A (M7.1):** Introduce a **pure function** (Python and/or Rust mirror for parity) that maps: `tenant_id`, correlation id, artifact digest, policy bundle version, risk class, and existing per-control outcomes **if already available** → `RuntimeGovernanceContext` → optional `RuntimeGovernanceSummary` in response **enrichment**.
- **Non-goals for M7.1:** Changing when evaluate returns 4xx/5xx, changing shadow mode behavior, or changing event append semantics (see existing `rust/tests/runtime_evaluate_http.rs`).
- **Contract tests:** Add tests that parse **new** optional keys only when present; old clients ignore unknown keys.
- **Parity:** If both Python and Rust expose evaluate-related types, keep field names aligned or document a stable JSON schema version field once introduced.

---

## 6. RBAC integration strategy

- **M7.6 only** applies RBAC to **management** surfaces (e.g. catalog admin, override administration, export job configuration) — routes enumerated in PR description and `docs/governance/rbac_permissions.v1.yaml` deltas.
- **Evaluate path:** Remains authenticated as today (API keys / existing auth); **no** permission matrix check on evaluate until a **separate** product decision beyond M7.7 default scope.
- **Principals:** Reuse M2 role bindings; enforce **explicit scope** (tenant/team/project) on management mutations only.
- **Failure mode:** 403 with stable error code string for RBAC denial; never leak other tenants’ resource existence.

---

## 7. Dataset lineage integration strategy

- **Source of truth:** M4 dataset governance artifacts (ids + digests already validated by M6 rules).
- **M7.3:** Resolver runs **after** evaluate core completes; inputs are **opaque** dataset ids and digests from caller or internal registry lookup **read-only**.
- **Shadow:** Enrichment may include `dataset_lineage_refs: []` or omitted when unknown; mismatches logged in tests or structured **non-blocking** warnings inside enrichment only.
- **Future (post M7.7):** Optional blocking only under opt-in policy (not part of M7.3).

---

## 8. Human override integration strategy

- **M3 linkage:** `override_id` from override store or request header (product decision per API design — **no new endpoint** in M7.x; use existing evaluate request fields if available, or enrichment from server-side lookup by `runtime_decision_id`).
- **M7.4 (implemented):** Request JSON `override_ref` on `POST /v1/runtime/evaluate` carries **`override_id`** + **`target_decision_id`** (trimmed, non-empty). **`target_decision_id`** must match the generated **`decision_id`** **or** **`runtime_<correlation_id>`**; mismatch ⇒ **400** `VALIDATION_ERROR`. Echoed in **`governance_enrichment.override_ref`** (same JSON as HTTP). **Shadow metadata only** — **no bypass authorization**, **no RBAC/SoD enforcement** on this path yet.
- **`off`/`shadow` global enforcement (`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT`):** Valid `override_ref` remains **audit metadata only** — it cannot convert **`INVALID`/`BLOCKED`** → **`VALID`**. **`enforced`** + allowlisted tenant may elevate failures from lineage/context/mapping per **`runtime_enforcement_gate.md`**; **`override_ref` alone still cannot authorize bypass**.
- **Invariant:** Invalid `override_ref` fails the request with **400** (`VALIDATION_ERROR`, fail-fast) — it never weakens outcomes for malformed requests on other tenants.

---

## 9. Audit export integration strategy

- **M7.5 (implemented in this planning bundle):** From a synthetic or request-assembled `AuditExportRequest`, call `evaluate_evidence_completeness` (M5) and assemble a **manifest plan**: list of control ids, evidence ref slots, completeness status, dataset lineage refs, override refs, AI Act requirement refs, and deterministic manifest digest — **no file I/O, no network export**.
- **Linkage:** Manifest references `runtime_decision_id`, `correlation_id`, and policy bundle version from M6 context.
- **Separation:** Export **execution** remains a later phase; this PR is documentation + pure assembly + unit tests. It does not generate production immutable packages.

---

## 9.1 M7.5–M7.8 status card

| Milestone | Documentation / artifact | Runtime effect |
|-----------|-------------------------|----------------|
| **M7.5** | `audit_export_manifest` helper + docs | Manifest planning helper only |
| **M7.6** | `rbac_enforcement_plan.md` | RBAC scopes management APIs future |
| **M7.7** | `runtime_enforcement_gate.md` | Human NO-GOs + operational checklist |
| **M7.8** | **`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT*` wiring** | Implements default-off summaries + enforced gate for explicitly allowlisted tenants |

Sequence now:

1. Keep governance enforcement **OFF** globally until operators validate previews.
2. Enable **`shadow`** to train telemetry / warnings without flipping verdict semantics.
3. Enable **`enforced`** only alongside `GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT_TENANTS=<allowlist>` + readiness sign-off (**`/ready`** + audit stakeholders).

---

## 10. AI Act / control mapping integration strategy

- **M1:** Control catalog remains authoritative for `control_id` strings attached to evaluations.
- **M7.2:** Maintain a **versioned** mapping table (YAML or DB later; **YAML/fixtures in repo** for M7.2 to avoid migrations): `reason_code` → `{ control_id, ai_act_requirement_refs[] }`.
- **M6:** `ai_act_requirement_refs` populated only from validated mapping, never free-text from users.
- **Drift handling:** Unknown reason codes escalate to sentinel **`WARN`** summaries for **`shadow`**, and **`FAIL` → `BLOCKED` (`unknown_reason_code`) for allowlisted tenants when governance enforcement resolves to **`enforced`**.

---

## 11. Required test matrix

| Area | Tests |
|------|-------|
| **M6 regression** | Full `python/tests/test_runtime_governance_integration.py` unchanged semantics. |
| **M7.1 contract** | Rust HTTP tests: existing cases pass; new cases optional keys only. |
| **M7.2 mapping** | Unit: every fixture reason code resolves; unknown code behavior deterministic. |
| **M7.3 lineage** | Unit: valid/invalid digests; empty lineage; ordering stable in tuple. |
| **M7.4 override** | Unit: match/mismatch `target_decision_id`; None override. |
| **M7.5 manifest** | Unit: completeness aggregation deterministic; no side effects. |
| **M7.6 RBAC** | Unit + integration: allow/deny matrix for one management route; cross-tenant denied. |
| **M7.7 gate** | Config parsing tests: default off; on requires explicit flag; document rollback. |
| **Cross-language** | If dual implementation: golden JSON vectors for enrichment blob. |

Commands expected green each PR: `python -m pytest`, `cargo test --manifest-path rust/Cargo.toml`, `python scripts/gate_reports.py`, `make gate`.

---

## 12. Failure semantics

| Layer | Behavior |
|-------|----------|
| **Core evaluate** | Unchanged through M7.1–M7.6: existing fail-closed and validation rules. |
| **Governance validation** | `BLOCKED` = context invalid / policy mismatch / unknown codes (post M7.2 in enrichment path). |
| **Governance verdict** | `INVALID` = at least one control `FAIL` in context (informational in shadow; must not remap HTTP unless M7.7). |
| **RBAC (M7.6)** | 403 on management denial; no silent downgrade. |
| **Shadow attach failures** | Omit enrichment subsection or return empty arrays; never throw 500 from enrichment alone. |

---

## 13. Migration strategy

- **No database migrations** in M7.1–M7.6.
- **Configuration only:** Feature flags and YAML mapping files versioned in repo (`v1`, `v2` suffix pattern aligned with RBAC/control docs).
- **Breaking changes:** If JSON enrichment must break, bump a `governance_enrichment_version` field and support N and N-1 for one release (document in operator runbook).

---

## 14. Rollout strategy

1. **Dev / CI:** All enrichment and shadow fields enabled in tests.
2. **Staging:** Enable M7.1 enrichment for internal tenants; monitor payload size and latency (enrichment must be O(n) in controls, no network I/O in hot path).
3. **Production:** Ship M7.1–M7.5 with flags default **off** or enrichment **omitted** until operator enables per tenant.
4. **M7.6:** Roll out management API RBAC tenant-by-tenant with break-glass admin role audited.
5. **M7.7:** Phased opt-in: single tenant pilot → review → expand; instant rollback by flag.

---

## 15. NO-GO conditions

Do **not** merge or enable when:

- Core `/v1/runtime/evaluate` tests regress (status codes, body fields relied on by Phase 2 contract).
- Enrichment causes **500** on benign missing optional data.
- Raw user content appears in governance context or audit manifest plan.
- RBAC wildcard or cross-tenant read slips into management or evaluate paths.
- Ledger writes or DB migrations appear in an M7.1–M7.6 PR without explicit scope change.
- Compliance-summary or unrelated product surfaces change “for convenience.”
- M7.7 opt-in is ambiguous (multiple flags, default-on in production, or missing runbook rollback).

---

## References

- M1: `docs/reports/repo-debt-audit-and-cleanup.md`
- M2: `docs/governance/rbac_permissions.v1.yaml`, `docs/reports/repo-debt-audit-and-cleanup.md`
- M3: `docs/reports/repo-debt-audit-and-cleanup.md`
- M4: `docs/reports/repo-debt-audit-and-cleanup.md`
- M5: `docs/governance/audit_exports.md`, `docs/reports/repo-debt-audit-and-cleanup.md`
- M6: `docs/governance/runtime_integration.md`, `docs/reports/repo-debt-audit-and-cleanup.md`
