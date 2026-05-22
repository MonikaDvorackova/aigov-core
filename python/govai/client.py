from __future__ import annotations

from typing import Any, Mapping, Optional

import requests


class GovAIError(Exception):
    """Base error for the GovAI SDK."""


class GovAIHTTPError(GovAIError):
    """Raised when the server returns a non-success HTTP status."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response: requests.Response | None = None,
        body_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response
        self.body_text = body_text


class GovAIAPIError(GovAIError):
    """Raised when the JSON body indicates failure (e.g. ``ok: false``) with HTTP 200."""

    def __init__(self, message: str, payload: dict[str, Any]) -> None:
        super().__init__(message)
        self.payload = payload


class GovAIClient:
    """
    Thin HTTP client for the GovAI audit API (Rust core).

    ``base_url`` should be the origin only (e.g. ``http://127.0.0.1:8088``). Stable paths and
    JSON shapes are defined in the repo root ``api/govai-http-v1.openapi.yaml`` (v1 contract).
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        *,
        default_project: Optional[str] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._default_project = (default_project or "").strip() or None
        self._session = requests.Session()
        self._session.headers.setdefault("Accept", "application/json")
        if api_key:
            self._session.headers["Authorization"] = f"Bearer {api_key}"
        if self._default_project:
            self._session.headers["X-GovAI-Project"] = self._default_project

    @property
    def base_url(self) -> str:
        return self._base_url

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self._base_url}{path}"

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int] | None = None,
        json_body: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout: float = 30.0,
        raise_on_body_ok_false: bool = False,
    ) -> Any:
        """
        Perform an HTTP request and parse a JSON response.

        Raises :class:`GovAIHTTPError` on non-success HTTP status.
        If ``raise_on_body_ok_false`` is True and the decoded JSON is a dict with
        ``ok`` equal to ``False``, raises :class:`GovAIAPIError`.
        """
        url = self._url(path)
        kwargs: dict[str, Any] = {"timeout": timeout}
        if params is not None:
            kwargs["params"] = dict(params)
        if json_body is not None:
            kwargs["json"] = json_body
        if headers is not None:
            kwargs["headers"] = dict(headers)

        try:
            response = self._session.request(method.upper(), url, **kwargs)
        except requests.RequestException as e:
            raise GovAIHTTPError(f"request failed: {e}") from e

        body_text = response.text if response.text else None

        if not response.ok:
            message = f"HTTP {response.status_code}"
            if body_text:
                message = f"{message}: {body_text[:2000]}"
            try:
                err = response.json()
                if isinstance(err, dict) and err.get("error") is not None:
                    message = f"HTTP {response.status_code}: {err.get('error')}"
            except ValueError:
                pass
            raise GovAIHTTPError(
                message,
                status_code=response.status_code,
                response=response,
                body_text=body_text,
            )

        try:
            data: Any = response.json()
        except ValueError as e:
            raise GovAIHTTPError(
                f"response is not valid JSON (HTTP {response.status_code})",
                status_code=response.status_code,
                response=response,
                body_text=body_text[:500] if body_text else None,
            ) from e

        if raise_on_body_ok_false and isinstance(data, dict) and data.get("ok") is False:
            err_msg = data.get("error")
            if not isinstance(err_msg, str) or not err_msg.strip():
                err_msg = "API returned ok: false"
            raise GovAIAPIError(err_msg, data)

        return data

    def submit_event(self, event: dict[str, Any]) -> dict[str, Any]:
        from .evidence import submit_event

        return submit_event(self, event)

    def get_bundle(self, run_id: str) -> dict[str, Any]:
        from .bundle import get_bundle

        return get_bundle(self, run_id)

    def get_bundle_hash(self, run_id: str) -> str:
        from .bundle import get_bundle_hash

        return get_bundle_hash(self, run_id)

    def get_compliance_summary(self, run_id: str) -> dict[str, Any]:
        from .api import get_compliance_summary

        return get_compliance_summary(self, run_id, timeout=30.0)

    def verify_chain(self) -> dict[str, Any]:
        from .verify import verify_chain

        return verify_chain(self)

    def get_usage(self, *, project: str | None = None) -> dict[str, Any]:
        from .usage import get_usage

        return get_usage(self, project=project)

    def get_functions_v2_flight_pack(
        self,
        run_id: str,
        *,
        extra_headers: Mapping[str, str] | None = None,
        timeout: float = 60.0,
    ) -> Any:
        """Enterprise read: requires Supabase JWT in ``extra_headers`` (``Authorization``)."""
        path = f"/api/functions/v2/{run_id}/flight-pack"
        return self.request_json("GET", path, headers=extra_headers, timeout=timeout)

    def get_functions_v2_executive_summary(
        self,
        run_id: str,
        *,
        extra_headers: Mapping[str, str] | None = None,
        timeout: float = 60.0,
    ) -> Any:
        path = f"/api/functions/v2/{run_id}/executive-summary"
        return self.request_json("GET", path, headers=extra_headers, timeout=timeout)

    def get_functions_v2_legal_evidence_manifest(
        self,
        run_id: str,
        *,
        extra_headers: Mapping[str, str] | None = None,
        timeout: float = 60.0,
    ) -> Any:
        path = f"/api/functions/v2/{run_id}/legal-evidence-manifest"
        return self.request_json("GET", path, headers=extra_headers, timeout=timeout)

    def get_functions_v2_governance_scorecard(
        self,
        run_id: str,
        *,
        extra_headers: Mapping[str, str] | None = None,
        timeout: float = 60.0,
    ) -> Any:
        path = f"/api/functions/v2/{run_id}/governance-scorecard"
        return self.request_json("GET", path, headers=extra_headers, timeout=timeout)
