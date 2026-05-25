# OpenAI-style runtime audit

Shows how a chat-style application records **mocked** model input, model output, and policy evaluation as ledger evidence, then reads compliance summary, export, and verify.

No OpenAI API key is required. Model I/O is simulated locally.

## Environment

| Variable | Purpose |
|----------|---------|
| `GOVAI_AUDIT_BASE_URL` | `aigov_audit` base URL (default `http://127.0.0.1:8088`) |
| `GOVAI_API_KEY` | Bearer secret mapped in `GOVAI_API_KEYS_JSON` |
| `GOVAI_RUN_ID` | Ledger run identifier |
| `GOVAI_PROJECT` | Optional metadata label (`X-GovAI-Project`, not tenant isolation) |
| `GOVAI_EXAMPLE_EXECUTE` | Set to `1` to call the live runtime |

## Run

```bash
export GOVAI_EXAMPLE_EXECUTE=1
python3 examples/openai-runtime-audit/run_openai_runtime_audit.py
```

Mounted routes used: `POST /evidence`, `GET /compliance-summary/{run_id}`, `GET /api/export/{run_id}`, `GET /verify/{run_id}`.

## Expected verdict

Until the full governance lifecycle is appended, the compliance summary is usually **BLOCKED** even after `evaluation_reported` with `passed=true`. That is expected for a minimal OpenAI-style trace.
