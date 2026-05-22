"""Typed errors for the runtime governance SDK (stdlib transport)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RuntimeSDKError(Exception):
    """Base class for SDK failures (validation, transport, or service contract)."""

    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


@dataclass(frozen=True)
class ValidationError(RuntimeSDKError):
    """Client-side validation failed before a request was sent."""


@dataclass(frozen=True)
class TransportError(RuntimeSDKError):
    """Network or I/O failure talking to the audit service."""

    cause: BaseException | None = None


@dataclass(frozen=True)
class ServiceHTTPError(RuntimeSDKError):
    """Non-2xx HTTP response from the audit service."""

    status_code: int
    body: Mapping[str, Any] | str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.message} (HTTP {self.status_code})"


@dataclass(frozen=True)
class EvidenceIngestRejected(RuntimeSDKError):
    """HTTP 200 with ``ok: false`` on ``POST /evidence`` (policy / validation / duplicate)."""

    details: Mapping[str, Any]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


@dataclass(frozen=True)
class MalformedResponse(RuntimeSDKError):
    """Response body was not JSON or did not match the minimum expected contract."""

    status_code: int | None = None
