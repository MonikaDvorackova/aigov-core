# Runtime governance examples

Illustrative scripts for embedding **GovAI** (`POST /evidence`, `GET /compliance-summary`) from application runtimes using the **stdlib HTTP** Python SDK under `python/aigov_py/runtime/`.

- **Canonical contracts** — [`../../api/govai-http-v1.openapi.yaml`](../../api/govai-http-v1.openapi.yaml)
- **Narrative docs** — [`../../docs/runtime/overview.md`](../../docs/runtime/overview.md)

| File | Purpose |
|------|---------|
| [`fastapi-example.py`](fastapi-example.py) | FastAPI wiring with lazy imports (`pip install 'aigov-py[server]'`). |
| [`langchain-example.py`](langchain-example.py) | Stdlib hook pattern you can call from LangChain callbacks. |
| [`openai-gateway-example.py`](openai-gateway-example.py) | Gateway metadata merged into evidence payloads. |
| [`sample-runtime-policy.json`](sample-runtime-policy.json) | **Documentation-only** sample describing runtime policy knobs (not enforced by these scripts). |

**Safety:** do not put API keys in source; use environment variables (`GOVAI_API_KEY`, `GOVAI_AUDIT_BASE_URL`, `GOVAI_PROJECT`).
