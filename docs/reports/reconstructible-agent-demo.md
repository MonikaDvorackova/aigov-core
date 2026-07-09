# Reconstructible Agent Demo

## Summary

Adds `examples/reconstructible-agent-demo/` — a developer-facing runtime demonstrator with `run_demo.py`, offline `viewer/index.html`, export replay under `exports/<run_id>.json`, operator documentation, and `make reconstructible-demo-check` wired into `govai-ci.yml`. The demo exercises AIGov Core mounted routes only (`POST /evidence`, `GET /compliance-summary`, `GET /api/export`, `GET /verify`, `GET /bundle-hash`). Mocked agent text and tool results; live ledger ingest and verdict reads. No commercial SaaS dashboard or platform workflow routes.

## Evaluation gate

Evaluation evidence contributes to **deterministic ledger-authoritative verdicts**. The demo appends `evaluation_reported` with `passed: true` as part of the governance lifecycle. Compliance summary and audit export derive `evaluation_passed` and overall `verdict` from ledger projection—not from client-side scores or observability metrics. A failed evaluation would yield **INVALID** via the same projection rules.

## Human approval gate

Approval evidence contributes to **deterministic ledger-authoritative verdicts**. The demo records compliance summary while approval is still missing (typically **BLOCKED**), then appends `human_approved` and `model_promoted`, and re-reads summary and export until **VALID** when policy requirements are satisfied. Export includes `human_approved` in `evidence_events` and human-approval fields under `decision`; the replay viewer surfaces the approval gate explicitly.

## Replay semantics

Replay is **export-driven**: `GET /api/export/:run_id` produces `aigov.audit_export.v1` with ordered `evidence_events` and `evidence_hashes.log_chain`. The viewer loads saved JSON locally and displays timeline order, tool/policy/approval gates, ledger `decision.verdict`, and hash-chain linkage checks. `GET /verify/:run_id` confirms tenant chain validity at runtime. Deterministic replay means the same ledger bytes yield the same export hashes and verdict projection.

## Verification

```bash
make reconstructible-demo-check
make reference-integrations-check
make core-runtime-examples-check
make gate
cd rust && cargo build --locked --bin aigov_audit && cargo test --locked
```

Live demo (operator-hosted `aigov_audit`):

```bash
export GOVAI_EXAMPLE_EXECUTE=1
export GOVAI_API_KEY=test-key
python3 examples/reconstructible-agent-demo/run_demo.py
```

CI runs structure and contract checks offline; it does not start a long-lived HTTP server.
