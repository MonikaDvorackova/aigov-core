# FastAPI middleware reference

Demonstrates middleware hooks around an AI HTTP handler:

1. `http_request_received`
2. `ai_decision_started`
3. Evidence appended via `POST /evidence`
4. `ai_decision_completed`
5. Compliance summary read (logged or returned on `X-GovAI-Verdict`)

## Run (simulation, no server)

```bash
export GOVAI_EXAMPLE_EXECUTE=1
python3 examples/fastapi-runtime-middleware/run_fastapi_middleware_demo.py
```

## Run (optional HTTP server)

```bash
pip install 'aigov-py[server]'
export GOVAI_API_KEY=...
export GOVAI_AUDIT_BASE_URL=http://127.0.0.1:8088
python3 examples/fastapi-runtime-middleware/app.py
curl -sS -X POST http://127.0.0.1:8098/ai/decide \
  -H "Authorization: Bearer $GOVAI_API_KEY" \
  -H "X-GovAI-Run-Id: fastapi-demo-1"
```

Uses mounted routes only (`POST /evidence`, `GET /compliance-summary/{run_id}`).
