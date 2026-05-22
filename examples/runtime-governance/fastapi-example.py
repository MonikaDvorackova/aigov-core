#!/usr/bin/env python3
"""Minimal FastAPI app showing ``RuntimeGovernanceClient`` wiring (optional deps).

Install server extras: ``pip install 'aigov-py[server]'`` (from ``python/``).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running from repo root without editable install
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "python"))


def main() -> None:
    try:
        from fastapi import Depends, FastAPI, HTTPException
        from fastapi.responses import JSONResponse
    except ImportError:
        print("Install FastAPI: pip install 'aigov-py[server]'", file=sys.stderr)
        raise SystemExit(2) from None

    from aigov_py.runtime import RuntimeGovernanceClient
    from aigov_py.runtime.adapters.fastapi import make_client_dependency

    base = os.environ.get("GOVAI_AUDIT_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
    key = os.environ.get("GOVAI_API_KEY")
    project = os.environ.get("GOVAI_PROJECT")

    def _factory() -> RuntimeGovernanceClient:
        return RuntimeGovernanceClient(base, api_key=key, project=project, timeout_sec=15.0)

    app = FastAPI(title="GovAI runtime example")
    dep = make_client_dependency(_factory)

    @app.get("/compliance/{run_id}")
    def compliance(run_id: str, client: RuntimeGovernanceClient = Depends(dep)) -> JSONResponse:
        try:
            summary = client.get_compliance_summary(run_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return JSONResponse(content=dict(summary.raw))

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8099")))


if __name__ == "__main__":
    main()
