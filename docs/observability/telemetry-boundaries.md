# Telemetry boundaries

The Phase 17 observability layer is intentionally **narrow**. This page documents what it does **not** do so the boundary is unambiguous for operators, contributors, and reviewers.

## Out of scope

| Boundary | Position |
|----------|----------|
| Runtime enforcement | Phase 17 does not change `POST /evidence`, `GET /compliance-summary`, or `POST /v1/runtime/evaluate` behaviour. Verdict semantics (VALID / INVALID / BLOCKED) remain governed by the audit service. |
| Billing | Phase 17 introduces no new billing metrics, billing webhooks, or Stripe configuration. See [`docs/billing.md`](../billing.md) for the canonical billing surface. |
| Ledger | Snapshots are **not** ledger entries; they are operator-side summaries. The append-only ledger semantics are unchanged. |
| Database schema | No migrations are introduced by this phase; the snapshot schema is described only in JSON and validated by stdlib Python. |
| Evidence payloads | Snapshots must not embed evidence payloads, run identifiers tied to a tenant, or PII. They are bounded to operational counters and booleans. |

## In scope

- Manifest, validators, scoring, diagnostics, and report generation for **operational snapshots**.
- Documentation and example drivers that operators can run **without** a hosted audit service.
- A deterministic Makefile aggregate (`make observability-check`) that ties the above into the existing `make gate` documentation-report gate.

## Data handling

- Snapshots are stored alongside the example file under [`examples/observability/`](../../examples/observability/). Real operator snapshots should be stored in operator-controlled systems, not in this repository.
- Validators read snapshots from the filesystem only; there are no network calls.

## Cross-references

- Runtime evaluate semantics: [`docs/governance/runtime_integration.md`](../governance/runtime_integration.md)
- Billing: [`docs/billing.md`](../billing.md)
- Regulatory boundaries: [`docs/regulatory/README.md`](../regulatory/README.md)
