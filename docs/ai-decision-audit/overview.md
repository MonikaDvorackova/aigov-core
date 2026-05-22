# AI decision flight recorder and multi-agent trace audit

This documentation matches **implemented** behavior in the Rust service and dashboard. It is not a roadmap document.

## Audit backend (hosted product layer)

The **audit backend** is the GovAI service that hosts evidence ingest, ledger storage, billing, and authenticated management routes (`/api/me`, tenant console, CRM export). It is broader than the AI trace tables alone.

## Decision flight recorder (operational telemetry)

The **decision flight recorder** is the append-only Postgres table `govai_ai_decision_trace_events` and the HTTP API under `/api/ai-decision-traces/*`. It records model identity, content hashes, agent roles, delegations, tool calls, policy evaluation rows, human gate states, and a **telemetry** `final_audit_verdict` (`VALID`, `INVALID`, `BLOCKED`, `UNKNOWN`) carried on the `completed` event.

## Multi-agent trace audit

**Multi-agent** behavior is captured with `delegation` events (`parent_agent_id`, `child_agent_id`, `child_role`) and optional `tool_call` / `step` events. The export aggregate (`trace_version: 2`) folds the append-only stream into a stable JSON document including `agents.delegations`, **hash-chain integrity** (`trace_integrity`), **delegation graph analysis** (`agents.delegation_graph`), **deterministic verdict derivation** (`derived_audit_verdict`, `verdict_consistent`), **explainability** blocks, **human approval workflow** metadata, and **`govai_functions_v2`** extensions (appeals, incidents, monitoring, seals, legal evidence references, certification marks, business impact, executive briefs) when those events are present.

## GovAI Functions 2.0 read APIs

Enterprise **`GET /api/functions/v2/{run_id}/*`** routes build flight-pack, executive, legal manifest, and scorecard views from the same trace stream. See **`docs/govai-functions-2.md`** and the in-repo **`typescript-sdk/`** client for JWT-oriented integrations.

## Tenant console surface

`GET /api/tenant-console/snapshot` (**`snapshot_version: 3`**) includes an `ai_decision_audit` object when the snapshot succeeds:

- `ledger_scope`, `data_source`, `relation_to_compliance_summary`, `recent_traces`, `ai_decision_trace_read`
- When the team is ledger-bound and the caller may read traces, `data_source` is `postgres` and `recent_traces` lists recent runs with **integrity status**, **derived vs producer verdicts**, **delegation validity**, **explainability summary**, and **risk indicators** per run.

The dashboard **`/tenant-console`** renders this block from live JSON or from the typed **demo_fallback** payload (clearly labeled in UI when offline).

## Integrity and verdict enforcement

Each persisted event includes a **monotonic `event_seq` per `(ledger_tenant_id, run_id)`** and a **SHA-256 hash chain** binding payload digest, predecessor hash, and timestamp. **`completed` events are rejected** unless `final_audit_verdict` matches the deterministic derivation from prior `policy_eval` outcomes (`400 VERDICT_MISMATCH` with a preview payload). Postgres rejects `UPDATE`/`DELETE` on trace rows for normal roles via trigger.

## Explainability and human gate payloads

`policy_eval` and `completed` support structured fields such as `reason_codes`, `triggered_controls`, `evidence_refs`, `policy_version`, `decision_rationale`, and `explanation_summary` (see validation in `rust/src/ai_decision_audit.rs`). `human_gate` requires approver identity and RFC3339 `approval_timestamp` when `approval_state` is `approved` or `rejected`, and validates `approval_state` / `override_state` enumerations.

## Compliance summary verdict (authoritative ledger)

**`GET /compliance-summary`** remains the only authoritative projection of **immutable ledger** compliance for a run. The flight recorder’s verdict and `policy_eval` outcomes are **operational** and may be used for investigations; they do not replace ledger semantics. Optional field `compliance_summary_run_id` on `trace_started` links identifiers when operators align them.

## RBAC

Product permissions `ai_decision_trace_read` and `ai_decision_trace_write` gate list/read/export vs create/append. They appear in the snapshot `rbac` echo alongside tenant console permissions.

## Examples

See [`../../examples/ai-decision-audit/README.md`](../../examples/ai-decision-audit/README.md).
