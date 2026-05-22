# Phase 3 runtime governance enforcement gate (M7.7 design lock → M7.8 implementation)

The Phase 3 final bundle **implements** opt-in governance enforcement behind **`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT`**, wired to **`POST /v1/runtime/evaluate`**, **`runtime_decision` ledger enrichment**, and **`GET /ready`** diagnostics.

The sections below preserve the original NO-GO and rollout semantics (M7.7) alongside what is **actually shipped**.

## Enforcement flag

Production enforcement stays behind a single explicit setting:

```text
GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT=off|shadow|enforced
```

Default is **`off`** in every environment (missing / empty / unknown values all normalize to **`off`**).

Modes:

| Mode | Behavior |
|------|----------|
| `off` | Governance enforcement is disabled. Existing **`GOVAI_RUNTIME_EVALUATE`** preview verdicts (**`disabled`** / **`shadow`**) behave as today. **`governance_summary`**, **`risk_class`** defaults (**`LIMITED`**), and ledger **`governance_summary`** enrichment are additive only. HTTP **`enforcement`** reports **`off`** (replacing legacy **`none`** metadata). |
| `shadow` | Computes **`governance_summary`** (warnings, lineage rule advisories). Does **not** change top-level **`verdict`** or stub **`control_evaluations`**. HTTP **`enforcement`** reports **`shadow`**. |
| `enforced` | May elevate failures into top-level **`BLOCKED`**/**`INVALID`** only for tenants explicitly allowlisted (**`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT_TENANTS`**). Operators must still independently validate rollout readiness (`/ready`, monitoring, SOC change control). Tenants excluded from that allowlist keep non-blocking **`shadow`**-style summaries (HTTP **`enforcement`** echoes **`shadow`**, **`governance_summary.enforced`** is **`false`**). Disabled runtime (**`runtime_not_enabled`**) verdicts remain pinned **`BLOCKED`**. |

Production **`enforced`** mode is explicit opt-in only. A default-on production configuration remains invalid under the NO-GO list below.

## Unknown reason-code policy (chosen)

Instead of pretending unknown tokens are SAFE, **`enforced`** + allowlisted tenancy maps any unrecognized **`reason_codes`** surfaced in governance evaluations through a synthetic **`FAIL`** **`GOVAI.GOVERNANCE.REASON_MAPPING`** control such that **`governance_summary.verdict`** becomes **`BLOCKED`** with **`unknown_reason_code`**. **`shadow`** (or **`enforced`** excluding the tenant allowlist) records the same sentinel as **`WARN`** commentary only.

**Readiness-aware “not enforceable yet” deferrals** beyond simple env guards remain product/operator tooling (outside this MVP).

## Tenant allowlist and readiness

`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT_TENANTS=tenant-a,tenant-b` trims whitespace-only entries after splitting on commas. Tenant membership is validated against API-key-derived ledger tenant identifiers (never from client-controlled headers alone).

**`GET /ready`** and **`GET /status`** expose **`runtime_governance_enforcement`**: **`configured_mode`**, **`tenant_allowlist_configured`**, **`enforceable`** (true iff global mode **`enforced`** AND allowlist has at least one tenant id), and **`reason_if_not_enforceable`**.

Original checklist for humans before turning on prod enforcement:

`enforced` mode requires:

- Tenant id present in an operator-managed allowlist.
- Runtime governance readiness passed for that tenant.
- Reason-code-to-control mapping coverage reviewed.
- Audit export traceability reviewed.
- Rollback flag tested in the target environment.

If the global flag is `enforced` but the tenant is not allowlisted, the tenant must remain non-blocking and emit an operator warning. If an allowlisted tenant lacks readiness, enforced evaluation must fail closed as `BLOCKED` until readiness is restored or the flag is rolled back.

## Rollback behavior

Changing `GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT` from `enforced` to `shadow` or `off` must stop blocking behavior without requiring a deploy or migration.

Rollback must not:

- Delete historical trace metadata.
- Rewrite previous decisions.
- Grant validity to a request that was already rejected.
- Require ledger repair.

## Verdict semantics

Future enforcement must preserve these meanings:

- `VALID`: governance context is complete and no control failed.
- `INVALID`: one or more evaluated controls failed.
- `BLOCKED`: governance context or required enforcement input is missing, inconsistent, or not ready for an enforced decision.

In `off`, governance semantics populate **`governance_summary`** metadata but never flip top-level **`verdict`**. **`shadow`** also leaves runtime verdict untouched. **`enforced`** (allowlisted) may remap verdicts derived from lineage / mapping / malformed-context failures into **`BLOCKED`**/**`INVALID`**, except when the preview runtime evaluator is **`disabled`** (`runtime_not_enabled`) — **`BLOCKED` stays pinned.

## Dataset enforcement

Dataset lineage enforcement is limited to **`enforced`** tenancy + optional **`risk_class`** on the request (**`HIGH`**):

- **`HIGH`** risk without refs -> `BLOCKED` with **`dataset_lineage_required`** for allowlisted tenants only.
- HIGH risk with missing lineage in `shadow` records a warning only.
- Without **`risk_class`** equal to **`HIGH`**, missing lineage carries no lineage block under this MVP (**`MINIMAL`** / **`LIMITED`** **[default]** / **`PROHIBITED`** omit the lineage gate). **`risk_class`** is ignored when **`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT`** is **`off`**.
- Dataset refs remain opaque identifiers; raw dataset records must not enter runtime governance or audit export manifests.

## Override enforcement

An `override_ref` alone is not approval.

Future override approval requires:

- RBAC authorization for the approving actor.
- Separation-of-duties compliance.
- Non-expired approval.
- Scope match to tenant and target decision.
- Target decision linkage.

An invalid override cannot turn `INVALID` or `BLOCKED` into `VALID`. Override failures in `enforced` mode remain `INVALID` or `BLOCKED` according to the underlying control/context failure; in `shadow`, they record warning metadata only.

## Reason-code and AI Act mapping

Every enforcement reason code must map to a stable control surface before **`enforced`** blocking is credible. Implemented behavior: **`enforced`** + allowlisted tenancy → unresolved tokens surface as **`BLOCKED`** with **`unknown_reason_code`** (**`FAIL`** sentinel); **`shadow`** or non-allowlisted tenancy → sentinel **`WARN`** only.

AI Act requirement refs are derived from reviewed control mappings. They are trace metadata and audit export references; they must not be accepted as free-form user-provided authority for enforcement.

## Audit export trace requirement

Every future enforced decision must be traceable into an audit export manifest plan:

- Runtime decision id or correlation id.
- Tenant id.
- Control ids.
- Reason codes.
- Evidence refs.
- Dataset lineage refs where applicable.
- Override refs where applicable.
- AI Act requirement refs where mapped.

The trace requirement is reference-only and must not introduce raw prompts, raw dataset records, raw user payloads, DB migrations, or production immutable package generation in this planning bundle.

## Failure semantics

| Failure | `off` | `shadow` | `enforced` (implementation) |
|---------|-------|----------|-------------------|
| Missing tenant allowlist | Advisory metadata only (`/ready enforceable=false`) | Advisory summaries + lineage warnings | Blocking only for tenants enumerated in **`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT_TENANTS`**; tenants absent from that list behave like **`shadow`** |
| Missing readiness for allowlisted tenant | No effect | Warning | `BLOCKED` |
| Missing HIGH-risk lineage | No effect | Warning | `BLOCKED` |
| Invalid override | No effect | Warning | Cannot validate bypass; remains `INVALID` or `BLOCKED` |
| Unknown reason-code mapping | No synthetic controls | Sentinel `WARN` | `FAIL` sentinel → **`BLOCKED`** (**`unknown_reason_code`**) |
| Audit trace assembly failure | No effect | Warning | `BLOCKED` unless explicitly classified as non-critical |

Failure behavior must never silently convert an invalid or blocked governance outcome into `VALID`.

## Rollout sequence

1. `off`: ship code paths disabled, verify runtime evaluate contract remains unchanged.
2. `shadow`: enable warnings and trace assembly for internal tenants, compare results with expected controls.
3. `enforced`: enable only after tenant allowlist, readiness, rollback drill, RBAC/SoD review, audit trace review, and product/security approval.

## Test matrix

| Area | Required tests before enforcement |
|------|-----------------------------------|
| Flag parsing | Default `off`; only `off`, `shadow`, `enforced` accepted |
| Production opt-in | `enforced` requires explicit config and tenant allowlist |
| Rollback | `enforced` to `shadow`/`off` stops blocking without migration |
| Dataset lineage | HIGH risk missing lineage warns in **`shadow`**, **`BLOCK`** in allowlisted **`enforced`** |
| Overrides | `override_ref` alone cannot approve; invalid override cannot make `VALID` |
| Reason mapping | Unknown mappings fail-closed in allowlisted **`enforced`** |
| AI Act refs | Derived from reviewed mappings only |
| Audit trace | Enforced decisions can build a reference-only manifest trace |
| Runtime evaluate regression | Existing runtime evaluate verdict behavior remains unchanged before opt-in |

## NO-GO conditions

Do not enable `enforced` when:

- The flag defaults to anything other than `off`.
- Production `enforced` mode can happen without explicit operator opt-in.
- Tenant allowlist is missing.
- Readiness checks are incomplete.
- Rollback cannot be performed by flag change.
- HIGH-risk dataset lineage behavior is ambiguous.
- Override approval lacks RBAC, SoD, expiry, or scope checks.
- Reason codes do not map to controls.
- AI Act mapping has not been reviewed.
- Audit export traceability is missing.
- Runtime evaluate contract tests regress.
