# Runtime Observability Diagnostics

## Summary

Extends `GET /status` with non-sensitive operational diagnostics (version, uptime, configuration flags, readiness component states, OTel linking hooks). Adds `govai runtime-diagnostics`, structured logging guidance, W3C trace context helpers (`trace_context` / `aigov_py.trace_context`), operator docs, and `make runtime-observability-check` in CI. No commercial platform UI, entitlements, or payment flows.

## Evaluation gate

**Replayed governance state remains ledger-authoritative.** Diagnostics and replay tooling read ledger projection and exports; `/status` does not mutate verdicts or evaluation outcomes. `evaluation_reported` events ingested into the ledger remain the source for `evaluation_passed` in compliance summary after deploy, restore, or observability-only outages.

## Human approval gate

**Approval evidence remains append-only operational evidence.** `/status` and `/ready` do not delete or rewrite `human_approved` events. Operators use diagnostics to detect stuck **BLOCKED** runs (missing approval) via compliance APIs and ops logs — not via fabricated client-side verdicts.

## Operator diagnostics

| Surface | Role |
|---------|------|
| `GET /health` | Liveness |
| `GET /ready` | Readiness (includes ledger append probe) |
| `GET /status` | Safe config + component diagnostics |
| `govai runtime-diagnostics` | CLI wrapper for all three |
| stderr JSON ops logs | Ingest, auth, readiness, replay failures |

## Verification

```bash
make runtime-observability-check
make runtime-packaging-check
make reconstructible-demo-check
make reference-integrations-check
make core-runtime-examples-check
make gate
cd rust && cargo build --locked --bin aigov_audit && cargo test --locked
cd ..
```

Optional live probe:

```bash
govai runtime-diagnostics --base-url http://127.0.0.1:8088
```
