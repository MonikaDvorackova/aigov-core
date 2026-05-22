# Runtime policy patterns

Hosted GovAI policy decides which **`event_type`** values and **`payload`** shapes are acceptable at **`POST /evidence`**. Application teams usually maintain a **parallel checklist** (lint rules, code review, and CI) so runtime instrumentation lines up with what the ledger expects.

## Sample checklist file

The repository ships a **documentation-only** JSON sample:

- [`../../examples/runtime-governance/sample-runtime-policy.json`](../../examples/runtime-governance/sample-runtime-policy.json)

It is validated by [`scripts/runtime_sdk_check.py`](../../scripts/runtime_sdk_check.py) for presence and schema version only — **not** consumed by the Rust runtime.

## Practical patterns

1. **Stable `event_id`** — use deterministic ids where safe; otherwise use UUIDv4 and treat duplicates as `409` responses from the service.
2. **Digest-first payloads** — prefer hashes over raw content for tool inputs and artefacts.
3. **Single verdict authority** — after posting evidence, read **`GET /compliance-summary`**; do not infer `VALID` locally.

## Related

- [Python SDK](python-sdk.md)
- [OpenAI gateway integration](openai-gateway-integration.md)
