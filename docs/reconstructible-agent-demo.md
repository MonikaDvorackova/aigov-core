# Reconstructible agent demo

The **reconstructible agent demo** (`examples/reconstructible-agent-demo/`) is a developer-facing runtime demonstrator. It shows how an AI agent workflow records **append-only evidence** on GovAI Core, derives a **ledger-authoritative compliance verdict**, exports an audit bundle, and replays the decision lifecycle offline.

This is not observability tooling, a SaaS dashboard, or enterprise admin UI.

## What “reconstructible” means

A run is reconstructible when an auditor can:

1. Read the **ordered evidence ledger** for a `run_id`
2. Recompute the same **compliance summary** and **export** from that ledger
3. Confirm **hash-chain integrity** (`GET /verify`, `evidence_hashes.log_chain` in export)
4. Relate **agent steps** (request → reasoning → tools → policy → decision → approval → promotion) to the final **VALID / BLOCKED / INVALID** verdict

GovAI Core does not reconstruct from distributed traces or log aggregators. The **ledger is authoritative**.

## Append-only evidence

Evidence is submitted with `POST /evidence`. Each event receives a stable `event_id` and is chained with `prev_hash` / `record_hash`. Events are never updated in place.

The demo appends, in order:

- Agent trace: `user_request`, `model_reasoning`, `tool_call`, `tool_output`, `policy_evaluation`
- Governance lifecycle: discovery, data registration, training, `evaluation_reported`, risk record/review
- Decision: `ai_decision_completed`
- Approval gate: `human_approved`, then `model_promoted`

Duplicate `event_id` values are rejected (`409 DUPLICATE_EVENT_ID`).

## Deterministic replay

**Deterministic replay** means the same ledger contents always produce the same:

- `GET /compliance-summary/:run_id` projection
- `GET /api/export/:run_id` document (`aigov.audit_export.v1`)
- Bundle hashes (`GET /bundle-hash/:run_id`)

The demo saves export JSON to `examples/reconstructible-agent-demo/exports/<run_id>.json` and opens `viewer/index.html` to render the timeline and hash continuity without calling the server again.

## Difference from observability traces

| Observability traces | GovAI reconstructible ledger |
|----------------------|------------------------------|
| Best-effort, sampled spans | Append-only, policy-checked events |
| Verdict often inferred offline | Verdict from **ledger projection** |
| Ordering approximate | **Evidence order** is contractual |
| Tool calls may be missing | Tool evidence is first-class event types |

OpenTelemetry-style traces help debug latency; they do not replace governance evidence for compliance decisions.

## Policy evaluation

`policy_evaluation` events (and ingest-time `policy.rs` enforcement on structured lifecycle events) record **what policy allowed or blocked** at decision time. The demo records a mocked `policy_evaluation` outcome linked to tool output event IDs.

Promotion still requires passed `evaluation_reported`, risk review, and `human_approved` per active policy configuration.

## Ledger-authoritative verdicts

The demo never invents a compliance outcome in client code. It reads:

- `GET /compliance-summary/:run_id` → `verdict`
- `GET /api/export/:run_id` → `decision.verdict`

and asserts they match after the full lifecycle. **VALID** only appears after required evidence (including `human_approved` and `model_promoted`) is present.

## Why evidence order matters

Compliance projection is a function of **which events exist and when they were appended**. The demo intentionally reads compliance summary **before** `human_approved` (typically **BLOCKED**) and again **after** promotion (**VALID**). Reordering or omitting approval evidence changes the verdict without any model rerun.

## Why human approval evidence matters

High-risk flows require explicit `human_approved` evidence with approver, scope, and linkage to assessment/risk records. The export surfaces `decision.human_approval` and includes the approval event in `evidence_events`. The replay viewer highlights the approval gate separately from tool and policy steps.

## Run the demo

```bash
# Terminal 1 — runtime (see repo README)
make run-audit

# Terminal 2
export GOVAI_EXAMPLE_EXECUTE=1
export GOVAI_API_KEY=test-key
python3 examples/reconstructible-agent-demo/run_demo.py
```

Open `examples/reconstructible-agent-demo/viewer/index.html` and load `exports/<run_id>.json`.

## CI

```bash
make reconstructible-demo-check
```

Validates demo files, mounted routes only, scope boundaries, and verdict semantics (no hardcoded compliance outcomes).

## Related

- [Runtime API contract](runtime-api-contract.md)
- [Reference integrations](reference-integrations.md)
- [Audit report](reports/reconstructible-agent-demo.md)
