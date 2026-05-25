# Deterministic Replay Engine

## Summary

Adds a Rust deterministic replay engine (`replay_validation`, `replay_projection`, `replay_engine`) that reconstructs governance, evaluation, and approval state from `aigov.audit_export.v1`, recomputes ledger-authoritative verdicts, validates event ordering and hash-chain continuity, and exposes `govai replay-audit-export` via `replay_audit_export_once`. Includes unit tests for stable replay, reordering, missing approval, chain breaks, verdict mismatch, duplicates, and cross-run determinism. No ledger, SaaS, or platform route changes.

## Evaluation gate

Evaluation evidence in replay remains **ledger-authoritative**. The engine projects `evaluation_passed` from `evaluation_reported` events and applies the same **INVALID** rule when evaluation failed. Replay explanations document the evaluation gate contribution; tampering with evaluation payloads surfaces as `events_content_sha256_mismatch` or `verdict_mismatch`.

## Human approval gate

Human approval evidence contributes to **deterministic ledger-authoritative verdicts** during replay. The engine detects missing `human_approved` before `model_promoted`, surfaces approval state in `projection.explanation`, and flags lifecycle errors when promotion precedes approval. Export `decision.verdict` must match replayed projection or replay reports `verdict_mismatch`.

## Replay determinism

Replay is **deterministic**: identical export JSON and default policy configuration yield identical `reconstructed_verdict`, `determinism_digest`, and validation outcomes. Event lists are sorted with stable `(ts_utc, event_type, event_id)` ordering before projection. The engine detects non-deterministic inputs (reordered events, duplicate IDs, broken `prev_hash` chain) as consistency failures.

## Verification

```bash
make gate
make reconstructible-demo-check
make reference-integrations-check
make core-runtime-examples-check
cd rust && cargo build --locked --bin aigov_audit && cargo build --locked --bin replay_audit_export_once && cargo test --locked
cd ../python && python -m pytest tests/test_replay_audit_export_cli.py -q
```

Operator replay:

```bash
govai export-run --run-id "$GOVAI_RUN_ID" > export.json
govai replay-audit-export --path export.json
govai replay-audit-export --path export.json --json
```
