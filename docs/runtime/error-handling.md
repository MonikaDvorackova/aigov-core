# Error handling (runtime SDK)

The runtime SDK raises **typed exceptions** from [`python/aigov_py/runtime/exceptions.py`](../../python/aigov_py/runtime/exceptions.py):

| Exception | When |
|-----------|------|
| `ValidationError` | Invalid client configuration (for example bad `base_url`, empty `run_id`, non-positive timeout). |
| `TransportError` | DNS, connection, timeout, or low-level I/O failures from `urllib`. |
| `ServiceHTTPError` | HTTP **4xx/5xx** responses (body parsed as JSON when possible). |
| `EvidenceIngestRejected` | HTTP **200** with `ok: false` on `POST /evidence` (policy, validation, duplicate `event_id`, …). |
| `MalformedResponse` | Non-JSON or unexpected JSON shape on an otherwise successful HTTP read. |

## Mapping to application errors

- Treat `EvidenceIngestRejected` as **operator-visible** failures (log structured `details`, do not retry blindly on duplicates).
- Treat `TransportError` / `ServiceHTTPError` as **transient or configuration** issues with backoff and circuit breaking as appropriate.

## Compliance summary

`GET /compliance-summary` returns HTTP **200** for both `ok: true` and `ok: false` bodies per OpenAPI. The client **always** returns a [`ComplianceSummary`](../../python/aigov_py/runtime/models.py); it does **not** raise merely because `ok` is false — callers decide how to handle non-success projections.

## Related

- [Python SDK](python-sdk.md)
- [Deployment guidance](deployment-guidance.md)
