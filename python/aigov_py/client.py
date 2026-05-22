from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests

from aigov_py.types import AssessmentCreate, AssessmentOut, GovaiError


class GovaiClient:
    """Enterprise HTTP helpers (e.g. ``POST /api/assessments``). Shapes: ``api/govai-http-v1.openapi.yaml``."""

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout_sec: float = 30.0):
        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key
        self.timeout_sec = timeout_sec

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"accept": "application/json"}
        if self.api_key:
            h["authorization"] = f"Bearer {self.api_key}"
        return h

    def _request(self, method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = urljoin(self.base_url, path.lstrip("/"))
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=self._headers(),
                json=json_body,
                timeout=self.timeout_sec,
            )
        except requests.RequestException as e:
            raise GovaiError(f"Network error calling Govai: {e}") from e

        if resp.status_code >= 400:
            details: Dict[str, Any]
            try:
                details = resp.json()
            except Exception:
                details = {"raw": resp.text}
            raise GovaiError("Govai API error", status_code=resp.status_code, details=details)

        try:
            return resp.json()
        except json.JSONDecodeError as e:
            raise GovaiError("Invalid JSON response from Govai", status_code=resp.status_code) from e

    def create_assessment(self, data: AssessmentCreate) -> AssessmentOut:
        payload = asdict(data)
        # Drop None fields
        payload = {k: v for k, v in payload.items() if v is not None}

        out = self._request("POST", "/api/assessments", json_body=payload)

        return AssessmentOut(
            id=str(out["id"]),
            system_name=str(out.get("system_name", data.system_name)),
            intended_purpose=str(out.get("intended_purpose", data.intended_purpose)),
            risk_class=str(out.get("risk_class", data.risk_class)),
            created_at=out.get("created_at"),
        )
