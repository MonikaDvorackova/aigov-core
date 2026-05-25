#!/usr/bin/env python3
"""Optional FastAPI server demonstrating middleware-style GovAI evidence hooks."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "python"))
sys.path.insert(0, str(_ROOT / "examples/reference-runtime-common"))

try:
    from fastapi import FastAPI, Request
    from starlette.middleware.base import BaseHTTPMiddleware
except ImportError:
    print("Install: pip install 'aigov-py[server]'", file=sys.stderr)
    raise SystemExit(2) from None

from aigov_py.runtime import RuntimeGovernanceClient

from run_fastapi_middleware_demo import record_decision_trace  # noqa: E402


def _client() -> RuntimeGovernanceClient:
    base = os.environ.get("GOVAI_AUDIT_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
    return RuntimeGovernanceClient(
        base,
        api_key=os.environ.get("GOVAI_API_KEY"),
        project=os.environ.get("GOVAI_PROJECT"),
        timeout_sec=15.0,
    )


class GovAIMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path != "/ai/decide":
            return await call_next(request)
        run_id = request.headers.get("X-GovAI-Run-Id") or os.environ.get("GOVAI_RUN_ID", "fastapi-run")
        decision_id = request.headers.get("X-GovAI-Decision-Id") or f"{run_id}-decision"
        client = _client()
        record_decision_trace(client, run_id, decision_id=decision_id, timeout=15.0)
        response = await call_next(request)
        summary = client.get_compliance_summary(run_id)
        response.headers["X-GovAI-Verdict"] = str(summary.verdict or "UNKNOWN")
        return response


app = FastAPI(title="GovAI FastAPI middleware reference")
app.add_middleware(GovAIMiddleware)


@app.post("/ai/decide")
async def decide() -> dict:
    return {"ok": True, "message": "mock AI decision"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8098")))
