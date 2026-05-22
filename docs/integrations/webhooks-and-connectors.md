# Webhooks and connector patterns

## Purpose

Document **safe, repeatable patterns** for integrating external systems with GovAI: outbound notifications from your stack, inbound automation (for example CI), and **Stripe billing webhooks** that already exist in hosted deployments—without implying unsupported first-party connectors.

## Integration overview

Two families:

1. **Inbound to GovAI** — HTTP clients (CI, services) call `POST /evidence`, `GET /compliance-summary`, exports. Authentication is bearer API keys unless the operator adds mTLS or IP allowlists.
2. **Outbound from GovAI / sidecar** — GovAI may emit webhooks in specific operator configurations; more commonly, **your orchestrator** receives vendor webhooks (Stripe, GitHub, identity) and translates them into evidence posts.

Hosted Stripe flows are documented in `docs/billing.md` (`POST /stripe/webhook`); treat billing webhooks as **integrity-critical** and verify signatures per Stripe documentation.

## Implementation steps

1. **Idempotency** — store event IDs from upstream webhooks; deduplicate before posting evidence to avoid duplicate ledger entries where that matters to policy.
2. **Signature verification** — verify vendor signatures on a dedicated route before any GovAI calls; reject early on mismatch.
3. **Mapping tables** — maintain a small translation layer from vendor payload fields to GovAI evidence schema; version the mapping when vendors change shape.
4. **Retries** — use exponential backoff for `5xx` from GovAI; do not retry blindly on `4xx` validation failures without fixing payload.
5. **Least privilege** — connector service accounts should only hold GovAI keys needed for posting evidence, not admin dashboard roles.

## Validation

- Run webhook handler unit tests with signed fixture payloads (Stripe provides test mode secrets).
- `python3 scripts/developer_integrations_check.py` for documentation presence in this repo.
- Staging drill: replay a captured webhook into a sandbox GovAI project and confirm summary transitions as expected.

## Failure modes

- **Replay attacks** — missing idempotency allows duplicate financial or governance events. Mitigation: idempotency keys and replay windows.
- **Clock skew** — Stripe signature tolerance too tight or too loose. Mitigation: follow Stripe guidance; monitor skew alarms.
- **PII in webhook logs** — logging full payloads violates policy. Mitigation: structured logs with hashed identifiers only.
