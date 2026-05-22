# Deployment guidance

## Configuration

- **`GOVAI_AUDIT_BASE_URL`** — absolute `https://` (or `http://` in local dev) origin of the audit API.
- **`GOVAI_API_KEY`** — bearer token for authenticated routes (`POST /evidence`, `GET /compliance-summary`, …).
- **`GOVAI_PROJECT`** — optional `X-GovAI-Project` header for usage attribution (does **not** determine tenant; see OpenAPI notes).

## Timeouts

Pick timeouts from SLOs: model pipelines often set **15–30s** for evidence posts and **5–15s** for compliance summary reads. The SDK default is **30s**; override per call with `timeout_sec=...`.

## Rotation and secrets

Load API keys from your platform secret store; avoid logging bearer tokens. Prefer **short-lived CI keys** in automation and **scoped keys** per environment.

## Health checks

Process health should probe **`GET /ready`** (readiness) separately from business calls — the runtime SDK intentionally focuses on ledger routes only.

## Related

- [Python SDK](python-sdk.md)
- [Error handling](error-handling.md)
- Hosted operations context: [`../operations/production-onboarding.md`](../operations/production-onboarding.md)
