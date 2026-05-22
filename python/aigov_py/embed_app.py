from __future__ import annotations

import os
from typing import List, Optional

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware


def _parse_allowed_ancestors(raw: str) -> List[str]:
    items = []
    for part in raw.split(","):
        v = part.strip()
        if not v:
            continue
        items.append(v)
    return items


class EmbedHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, allowed_frame_ancestors: Optional[List[str]] = None) -> None:
        super().__init__(app)
        self.allowed = allowed_frame_ancestors or []

    async def dispatch(self, request: Request, call_next) -> Response:
        resp: Response = await call_next(request)

        if "x-frame-options" in resp.headers:
            del resp.headers["x-frame-options"]

        if self.allowed:
            ancestors = " ".join(self.allowed)
        else:
            ancestors = "'none'"

        resp.headers["content-security-policy"] = f"frame-ancestors {ancestors};"
        resp.headers["referrer-policy"] = resp.headers.get("referrer-policy", "strict-origin-when-cross-origin")
        resp.headers["x-content-type-options"] = resp.headers.get("x-content-type-options", "nosniff")

        return resp


def create_embed_app() -> FastAPI:
    app = FastAPI(title="Govai Embed")

    allowed_raw = os.environ.get("GOVAI_EMBED_ALLOWED_ORIGINS", "")
    allowed = _parse_allowed_ancestors(allowed_raw)
    app.add_middleware(EmbedHeadersMiddleware, allowed_frame_ancestors=allowed)

    web_base = os.environ.get("GOVAI_WEB_BASE", "/dashboard")
    web_base = web_base.rstrip("/")

    @app.get("/embed", response_class=HTMLResponse)
    def embed_root(
        assessment_id: Optional[str] = Query(default=None),
        theme: str = Query(default="light"),
        locale: str = Query(default="en"),
    ) -> HTMLResponse:
        aid = assessment_id or ""
        src = f"{web_base}?embed=1&theme={theme}&locale={locale}&assessment_id={aid}"

        html = f"""<!doctype html>
<html lang="{locale}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Govai Embed</title>
    <style>
      html, body {{ height: 100%; margin: 0; background: transparent; }}
      iframe {{ width: 100%; height: 100%; border: 0; }}
    </style>
  </head>
  <body>
    <iframe
      src="{src}"
      allow="clipboard-read; clipboard-write"
    ></iframe>
  </body>
</html>
"""
        return HTMLResponse(content=html)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_embed_app()
