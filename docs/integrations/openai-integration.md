# OpenAI integration guide

## Purpose

Show how teams using **OpenAI APIs** (Chat Completions, Responses API, or enterprise proxies) can attach **GovAI evidence** and CI gates so model calls remain traceable without claiming GovAI performs legal certification.

## Integration overview

Typical pattern:

1. **Application code** calls OpenAI with your usual SDK (`openai` Python package or official Node SDK).
2. **Sidecar evidence** — after each governed action, emit structured events your policy expects (for example tool invocations, retrieval sources, human approvals) and `POST /evidence` to GovAI with the same `run_id` your pipeline uses.
3. **CI gate** — `govai check` or the composite GitHub Action ensures `VALID` before deploy.

GovAI does **not** wrap OpenAI network calls; it records what you assert happened and enforces policy on ingest.

## Implementation steps

1. **Choose run identity** — generate one `run_id` per deployment, session, or batch job; keep it stable across evidence posts for that unit of work.
2. **Emit events** — map OpenAI response metadata (model id, token usage if allowed by policy) into your evidence JSON schema; avoid storing secrets or raw PII if policy forbids it.
3. **Post to GovAI** — use `GovAIClient` or `curl` per `docs/customer-onboarding-10min.md`; handle `429`/`5xx` from either OpenAI or GovAI independently.
4. **Gate** — in GitHub Actions, run `verify-evidence-pack` after evidence submission when using artefact-bound flows.
5. **Observability** — optionally export OpenTelemetry spans (see `docs/integrations/opentelemetry-integration.md`) with `run_id` as a span attribute for cross-system joins.

## Validation

- Local: `govai check --run-id <uuid>` against a dev audit URL after posting minimal valid evidence.
- CI: workflow step that fails on non-zero exit from `govai check` or the composite action.
- `python3 scripts/developer_integrations_check.py` for documentation completeness in this repository.

## Failure modes

- **Double billing of responsibility** — assuming GovAI “validates” OpenAI safety settings. Mitigation: document human ownership; GovAI enforces **your** policy on **your** evidence.
- **Run ID churn** — new ID per request breaks summary aggregation. Mitigation: scope IDs deliberately and document lifecycle.
- **Evidence volume** — attaching full prompts violates retention policy. Mitigation: hash or redact per `docs/policy-contract.md` operator configuration.
