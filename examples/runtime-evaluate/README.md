# Runtime evaluate example (request shape)

`POST /v1/runtime/evaluate` is documented in:

- **[api/govai-http-v1.openapi.yaml](../../api/govai-http-v1.openapi.yaml)** (`RuntimeEvaluateRequest`)
- **[docs/governance/runtime_integration.md](../../docs/governance/runtime_integration.md)** — enrichment, **`GOVAI_RUNTIME_GOVERNANCE_ENFORCEMENT`**, and **advisory** vs blocking semantics

## Sample payload

See [`request.minimal.json`](request.minimal.json). It uses only **`correlation_id`** and **`action`** (required OpenAPI fields) plus a valid-format **`artifact_digest`** placeholder.

**Advisory controls:** rows under **`governance_summary.advisory_control_evaluations`** (for example **`source: capability_shadow`**) are **shadow-only** — they do **not** replace core enforcement or **`GET /compliance-summary`** eligibility.

## Try it (local Docker)

With the root **`docker compose`** stack running and a bearer token accepted by your server (see root **`docker-compose.yml`** `GOVAI_API_KEYS`):

```bash
curl -fsS http://127.0.0.1:8088/v1/runtime/evaluate \
  -H "Authorization: Bearer test-key" \
  -H "Content-Type: application/json" \
  -d @examples/runtime-evaluate/request.minimal.json
```

Replace **`test-key`** if your local server uses a different dev key.
