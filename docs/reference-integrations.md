# AIGov Core reference integrations

These examples show how real AI applications use **AIGov Core** (`aigov_audit`) as a ledger-authoritative audit runtime. They call only **mounted core routes** and do not start hosted SaaS, billing, or dashboard flows.

## What each example proves

| Example | Proves |
|---------|--------|
| [openai-runtime-audit](../examples/openai-runtime-audit/) | Mocked model input/output and policy evaluation appended as evidence; compliance summary, export, and verify read from the ledger |
| [fastapi-runtime-middleware](../examples/fastapi-runtime-middleware/) | HTTP middleware pattern: request received → AI decision started → evidence ingest → decision completed → compliance summary |
| [tool-call-audit](../examples/tool-call-audit/) | Tool call and tool output events linked to a final decision; export reconstructs tool use |
| [human-approval-runtime](../examples/human-approval-runtime/) | Risky run blocked without approval; `human_approved` evidence changes ledger projection and export |

## Prerequisites

1. Build and run the core runtime (`make run-audit` or `cargo run --bin aigov_audit`).
2. Configure tenant isolation on the server:

```bash
export GOVAI_API_KEYS="$GOVAI_API_KEY"
export GOVAI_API_KEYS_JSON="{\"$GOVAI_API_KEY\":\"local-dev\"}"
export GOVAI_LEDGER_DIR="$(pwd)/.govai-ledger"
export AIGOV_POLICY_DIR="$(pwd)/rust"
export AIGOV_ENVIRONMENT=dev
```

3. Client environment:

```bash
export GOVAI_AUDIT_BASE_URL="http://127.0.0.1:8088"
export GOVAI_API_KEY="<same secret as server allowlist>"
export GOVAI_RUN_ID="my-run-$(date +%s)"
export GOVAI_PROJECT="demo-project"   # metadata only
export GOVAI_EXAMPLE_EXECUTE=1
```

### Tenant isolation vs project label

- **Tenant isolation** comes only from `GOVAI_API_KEYS` + `GOVAI_API_KEYS_JSON` (fail-closed bearer → ledger tenant).
- **`X-GovAI-Project` / `GOVAI_PROJECT`** is optional metadata for attribution. It does **not** select or isolate tenants.

## How to run

```bash
python3 examples/openai-runtime-audit/run_openai_runtime_audit.py
python3 examples/fastapi-runtime-middleware/run_fastapi_middleware_demo.py
python3 examples/tool-call-audit/run_tool_call_audit.py
python3 examples/human-approval-runtime/run_human_approval.py
```

Optional FastAPI server: see [examples/fastapi-runtime-middleware/README.md](../examples/fastapi-runtime-middleware/README.md).

## Expected verdict behavior

AIGov Core derives compliance verdicts **deterministically** from append-only ledger evidence (see `GET /compliance-summary/{run_id}`).

| Situation | Typical verdict |
|-----------|-----------------|
| Single discovery or inference-only events | **BLOCKED** — missing required lifecycle evidence |
| Evaluation reported with `passed=true` but no promotion path | Often still **BLOCKED** |
| Full lifecycle including `human_approved` and `model_promoted` | **VALID** when policy gates are satisfied |

Minimal examples intentionally stop before a full promotion lifecycle so integrators can see **BLOCKED** as a normal outcome until they append the remaining evidence.

### Evaluation gate

`evaluation_reported` events (and evaluation outcomes in export) are **ledger-authoritative**. They contribute to deterministic compliance summary verdicts together with discovery, risk, and promotion state.

### Human approval gate

`human_approved` events are **ledger-authoritative**. They update approval projection and export `human_approval` fields, and they contribute to deterministic compliance summary verdicts (for example before `model_promoted` is allowed).

## CI drift check

```bash
make reference-integrations-check
```

Validates example directories, READMEs, mounted routes only, forbidden platform terms, and GovAI naming (not legacy vendor branding).

## Related docs

- [quickstart-runtime.md](quickstart-runtime.md)
- [runtime-api-contract.md](runtime-api-contract.md)
- [reports/core-reference-integrations.md](reports/core-reference-integrations.md)
