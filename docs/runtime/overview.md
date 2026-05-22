# Runtime governance documentation

GovAI’s **hosted audit contract** is unchanged: append-only **`POST /evidence`**, authoritative **`GET /compliance-summary`**, and **VALID / INVALID / BLOCKED** semantics defined in OpenAPI and enforced in Rust.

This folder documents how to **embed** those calls from production AI applications using the **stdlib-only** Python runtime SDK (`python/aigov_py/runtime/`), optional framework adapters, and runnable examples.

## Contents

- [Python SDK](python-sdk.md) — `RuntimeGovernanceClient`, models, timeouts, transport separation.
- [FastAPI integration](fastapi-integration.md) — lazy imports and dependency patterns.
- [LangChain integration](langchain-integration.md) — stdlib hooks you wire into callbacks.
- [OpenAI gateway integration](openai-gateway-integration.md) — routing metadata merged into payloads.
- [Runtime policy patterns](runtime-policy-patterns.md) — aligning local controls with hosted policy.
- [Error handling](error-handling.md) — typed exceptions and HTTP edge cases.
- [Deployment guidance](deployment-guidance.md) — base URLs, keys, and safe rollout.

## Examples

See [`../../examples/runtime-governance/README.md`](../../examples/runtime-governance/README.md).

## Canonical contract

- [`../../api/govai-http-v1.openapi.yaml`](../../api/govai-http-v1.openapi.yaml)
