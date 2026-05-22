"""HTTP transport and ``RuntimeGovernanceClient`` (stdlib ``urllib`` only)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, NoReturn, Protocol
from urllib.parse import urlencode, urljoin, urlparse

from aigov_py.canonical_json import canonical_bytes

from aigov_py.runtime.exceptions import (
    EvidenceIngestRejected,
    MalformedResponse,
    ServiceHTTPError,
    TransportError,
    ValidationError,
)
from aigov_py.runtime.models import ComplianceSummary, EvidenceEvent, EvidenceIngestResult


def _join_url(base: str, path: str) -> str:
    base_n = base.rstrip("/") + "/"
    return urljoin(base_n, path.lstrip("/"))


@dataclass(frozen=True)
class HttpRequestSpec:
    method: str
    url: str
    headers: dict[str, str]
    body: bytes | None


JsonObject = dict[str, Any]


class HTTPTransport(Protocol):
    def request_json(
        self,
        spec: HttpRequestSpec,
        *,
        timeout_sec: float | None = None,
    ) -> JsonObject: ...


class JsonHttpTransport:
    """Low-level JSON HTTP helper (separate from domain parsing)."""

    def __init__(
        self,
        *,
        opener: urllib.request.OpenerDirector | None = None,
        default_timeout_sec: float = 30.0,
    ) -> None:
        self._opener = opener or urllib.request.build_opener()
        self.default_timeout_sec = float(default_timeout_sec)
        if self.default_timeout_sec <= 0:
            raise ValueError("default_timeout_sec must be positive")

    def request_json(
        self,
        spec: HttpRequestSpec,
        *,
        timeout_sec: float | None = None,
    ) -> JsonObject:
        t = self.default_timeout_sec if timeout_sec is None else float(timeout_sec)
        if t <= 0:
            raise ValueError("timeout_sec must be positive")
        req = urllib.request.Request(
            spec.url,
            data=spec.body,
            headers=spec.headers,
            method=spec.method.upper(),
        )
        try:
            with self._opener.open(req, timeout=t) as resp:
                raw = resp.read()
                status = getattr(resp, "status", None) or resp.getcode()
        except urllib.error.HTTPError as e:
            _raise_for_http_error(e)
        except urllib.error.URLError as e:
            raise TransportError(f"network error: {e.reason}", cause=e) from e
        except TimeoutError as e:
            raise TransportError("request timed out", cause=e) from e
        except OSError as e:
            raise TransportError(f"io error: {e}", cause=e) from e

        if status is None or int(status) >= 400:
            raise MalformedResponse(f"unexpected HTTP status {status}", status_code=status)
        try:
            out = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise MalformedResponse("invalid JSON in response body", status_code=int(status)) from e
        if not isinstance(out, dict):
            raise MalformedResponse("expected JSON object at top level", status_code=int(status))
        return out


def _raise_for_http_error(e: urllib.error.HTTPError) -> NoReturn:
    """Normalize HTTPError: always raise ServiceHTTPError with parsed JSON when possible."""
    try:
        raw = e.read().decode("utf-8", errors="replace")
    except Exception as read_exc:  # pragma: no cover - defensive
        raise ServiceHTTPError(
            "HTTP error with unreadable body",
            status_code=e.code,
            body={"reason": str(read_exc)},
        ) from e
    try:
        body: Any = json.loads(raw)
    except json.JSONDecodeError:
        body = raw
    if isinstance(body, dict):
        details: Mapping[str, Any] | str = body
    else:
        details = raw
    raise ServiceHTTPError(
        "HTTP error from audit service",
        status_code=e.code,
        body=details,
    ) from e


class RuntimeGovernanceClient:
    """Submit evidence and read compliance summaries against a GovAI audit base URL."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        project: str | None = None,
        timeout_sec: float = 30.0,
        transport: HTTPTransport | None = None,
        transport_factory: Callable[[], HTTPTransport] | None = None,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValidationError("base_url must be an absolute http(s) URL with a host")
        self._base = base_url.rstrip("/")
        self._api_key = (api_key or "").strip() or None
        self._project = (project or "").strip() or None
        self._timeout = float(timeout_sec)
        if self._timeout <= 0:
            raise ValidationError("timeout_sec must be positive")
        if transport is not None and transport_factory is not None:
            raise ValidationError("pass at most one of transport and transport_factory")
        self._transport: HTTPTransport = transport or (
            transport_factory() if transport_factory else JsonHttpTransport(default_timeout_sec=self._timeout)
        )

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        if self._project:
            h["X-GovAI-Project"] = self._project
        return h

    def submit_evidence(self, event: EvidenceEvent, *, timeout_sec: float | None = None) -> EvidenceIngestResult:
        wire = event.to_wire_dict()
        body = canonical_bytes(wire)
        url = _join_url(self._base, "/evidence")
        hdrs = self._headers()
        hdrs["Content-Type"] = "application/json; charset=utf-8"
        spec = HttpRequestSpec(method="POST", url=url, headers=hdrs, body=body)
        try:
            resp = self._transport.request_json(spec, timeout_sec=timeout_sec)
        except ServiceHTTPError:
            raise
        except MalformedResponse:
            raise
        except TransportError:
            raise
        if resp.get("ok") is True:
            return EvidenceIngestResult.from_response(resp)
        if resp.get("ok") is False:
            raise EvidenceIngestRejected(
                str(resp.get("message") or resp.get("error") or "evidence ingest rejected"),
                details=resp,
            )
        raise MalformedResponse("evidence response missing ok boolean")

    def get_compliance_summary(self, run_id: str, *, timeout_sec: float | None = None) -> ComplianceSummary:
        rid = (run_id or "").strip()
        if not rid:
            raise ValidationError("run_id is required")
        qs = urlencode({"run_id": rid})
        path = f"/compliance-summary?{qs}"
        url = _join_url(self._base, path)
        spec = HttpRequestSpec(method="GET", url=url, headers=self._headers(), body=None)
        resp = self._transport.request_json(spec, timeout_sec=timeout_sec)
        return ComplianceSummary.from_response(resp)


def compliance_summary_url(base_url: str, run_id: str) -> str:
    """Deterministic URL builder (percent-encodes query)."""
    rid = (run_id or "").strip()
    qs = urlencode({"run_id": rid})
    return _join_url(base_url, f"/compliance-summary?{qs}")
