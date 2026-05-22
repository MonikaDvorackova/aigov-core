# OpenAI gateway integration

When traffic passes through an **LLM gateway** (model routing, fallbacks, or aggregators), embed **routing metadata** next to governance evidence so operators can correlate gateway decisions with ledger history.

Helpers live in [`python/aigov_py/runtime/adapters/openai_gateway.py`](../../python/aigov_py/runtime/adapters/openai_gateway.py):

- [`gateway_request_metadata`](../../python/aigov_py/runtime/adapters/openai_gateway.py) — stable keys (`gateway_route_id`, `upstream_model`, `correlation_id`, …).
- [`merge_payload`](../../python/aigov_py/runtime/adapters/openai_gateway.py) — shallow merge into an evidence `payload` dict.

## Contract reminder

The audit service still validates `event_type` and payload per **deployed policy**. These helpers do **not** bypass enforcement.

## Example

[`../../examples/runtime-governance/openai-gateway-example.py`](../../examples/runtime-governance/openai-gateway-example.py) (dry-run unless `GOVAI_EXAMPLE_EXECUTE=1`).

## Related

- [Python SDK](python-sdk.md)
- [Deployment guidance](deployment-guidance.md)
