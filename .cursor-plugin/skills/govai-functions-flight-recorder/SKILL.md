---
name: govai-functions-flight-recorder
description: Record and read GovAI Functions 2.0 AI decision flight telemetry (append-only traces, flight-pack APIs, validators).
---

# GovAI Functions 2.0 — flight recorder skill

Use this skill when implementing or reviewing **AI decision flight recorder** integrations (model hashes, tool calls, policy evaluation, human gates, appeals, incidents, monitoring, sealing, legal evidence references, certification marks).

## Principles

- **Append-only:** never UPDATE/DELETE trace rows; use new events to correct narrative.
- **Verdict authority:** `GET /compliance-summary` is the only authoritative immutable-ledger verdict; flight exports are operational telemetry.
- **Validation:** run `python3 scripts/validate_govai_functions_v2_pack.py --strict` on fixtures; in Cursor MCP call `govai_validate_functions_v2_pack` with the repo-relative JSON path.

## Key paths

- HTTP: `rust/src/ai_decision_http.rs`, `rust/src/govai_functions_v2.rs`
- Domain: `rust/src/ai_decision_audit.rs`, `rust/src/ai_decision_integrity.rs`
- Contract: `api/govai-http-v1.openapi.yaml`
- Docs: `docs/govai-functions-2.md`, `docs/ai-decision-audit/`

## Event vocabulary

See migration `rust/migrations/0021_govai_functions_v2_trace_event_types.sql` and `validate_append_event` in `ai_decision_audit.rs` for required payload fields.
