# Core adoption quickstart and examples

Audit of the adoption package for the completed GovAI Core `aigov_audit` runtime.

## Evaluation gate

Deliverables:

- `examples/basic-runtime-client/smoke-runtime.sh` — curl smoke for `POST /evidence`, `GET /compliance-summary/:run_id`, `GET /api/export/:run_id`, `GET /verify/:run_id`
- `examples/python-runtime-client/run_runtime_smoke.py` — stdlib SDK smoke for the same sequence
- `examples/python-runtime-client/langchain_tool_hook.py` — optional hook via `aigov_py.runtime.adapters.langchain`
- `docs/quickstart-runtime.md` — operator quickstart (API keys, tenant map, `make run-audit`)
- `docs/runtime-api-contract.md` — mounted-route contract
- `scripts/check_core_runtime_example_routes.py` — CI drift guard vs `govai_api.rs`

Constraints honored: no billing/Stripe/SaaS/dashboard flows, no fake readiness, no localhost polling in CI, explicit tenant mapping documentation.

## Human approval gate

Examples and docs state that:

- `GOVAI_API_KEYS` + `GOVAI_API_KEYS_JSON` are required for multi-tenant isolation when an allowlist is configured.
- `X-GovAI-Project` is metadata only.
- Minimal smoke may yield `BLOCKED` until the full lifecycle is ingested.

## Verification

```bash
cargo build --locked --bin aigov_audit
cargo test --locked
make gate
make core-runtime-examples-check
```

Operator smoke (manual, server running):

```bash
./examples/basic-runtime-client/smoke-runtime.sh
python3 examples/python-runtime-client/run_runtime_smoke.py
```
