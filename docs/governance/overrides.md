# Human override governance (lifecycle primitives only)

Phase 3 M3 introduces **metadata and pure-Python lifecycle validation** for human overrides (break-glass / exception paths). This slice does not change runtime enforcement.

## Scope

- **In scope**: request/decision datatypes, status enum, deterministic validation helpers (`validate_override_request`, `evaluate_override_decision`).
- **Out of scope**: HTTP APIs, database migrations, ledger writes, compliance-summary behavior, wiring overrides into policy or evaluation engines.

## Timezone safety (Phase 3 M3)

Phase 3 M3 **assumes timezone-aware UTC** `datetime` values for both `now` (passed into evaluation) and `expires_at` (on the request). Callers should not rely on **naive** datetimes as **production-authoritative** inputs: comparison behavior across naive vs aware values is a caller hazard until a single clock and normalization policy exists. **Datetime normalization and clock authority** will be enforced in a later phase when **API and persistence** layers are wired.

Overrides must always **reference a target decision or control**, include a **non-empty justification**, and carry an **expiration**. **Separation of duties** is modeled as: an **approver cannot be the same principal as the requester** for an approval transition.

## Lifecycle statuses

| Status    | Meaning (primitive)                                      |
|-----------|-----------------------------------------------------------|
| REQUESTED | Request recorded; awaiting approve/reject.                |
| APPROVED  | Approved while still within expiration (governance only). |
| REJECTED  | Rejected; cannot be approved later.                       |
| REVOKED   | Revoked after approval; requires a non-empty reason.        |
| EXPIRED   | Reserved for explicit expiry state (e.g. future wiring). |

There is **no production override enforcement** in this phase: callers must not treat these primitives as authorization or runtime bypass until wired with RBAC and audit.

## RBAC future wiring

Human approval of overrides should be constrained by RBAC. Future phases should require permission **`override.approve`** (and related governance permissions) before any service accepts an approval outcome. This document does not define API or storage.

## Determinism and fail-safe behavior

Validation and evaluation are **deterministic**: the same inputs yield the same results. Unknown actions are rejected with a stable error. Invalid transitions leave the decision **unchanged** and return errors rather than partially applying state.
