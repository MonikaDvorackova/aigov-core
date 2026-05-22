"""Deterministic domain models for runtime evidence and compliance summary reads.

Wire shapes follow ``api/govai-http-v1.openapi.yaml`` (``EvidenceEvent``,
``EvidenceIngestSuccess`` / ``EvidenceIngestError``, ``ComplianceSummary*``).
The SDK does **not** reinterpret hosted verdict semantics; it parses and surfaces
the server payload.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class ComplianceVerdict(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    BLOCKED = "BLOCKED"


def _strip_req(name: str, value: str) -> str:
    t = (value or "").strip()
    if not t:
        raise ValueError(f"{name} is required and must be non-empty after stripping")
    return t


@dataclass(frozen=True)
class EvidenceEvent:
    """One ``POST /evidence`` event (required fields per OpenAPI)."""

    event_id: str
    event_type: str
    ts_utc: str
    actor: str
    system: str
    run_id: str
    payload: Mapping[str, Any]
    environment: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _strip_req("event_id", self.event_id))
        object.__setattr__(self, "event_type", _strip_req("event_type", self.event_type))
        object.__setattr__(self, "ts_utc", _strip_req("ts_utc", self.ts_utc))
        object.__setattr__(self, "actor", _strip_req("actor", self.actor))
        object.__setattr__(self, "system", _strip_req("system", self.system))
        object.__setattr__(self, "run_id", _strip_req("run_id", self.run_id))
        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a mapping (e.g. dict)")

    def to_wire_dict(self) -> dict[str, Any]:
        """JSON-serialisable object for ``POST /evidence`` (insertion order preserved)."""
        out: dict[str, Any] = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "ts_utc": self.ts_utc,
            "actor": self.actor,
            "system": self.system,
            "run_id": self.run_id,
            "payload": dict(self.payload),
        }
        if self.environment is not None and str(self.environment).strip():
            out["environment"] = str(self.environment).strip()
        return out


@dataclass(frozen=True)
class EvidenceIngestResult:
    """Subset of a successful ``EvidenceIngestSuccess`` response."""

    ok: bool
    record_hash: str
    policy_version: str
    environment: str
    raw: Mapping[str, Any]

    @classmethod
    def from_response(cls, body: Mapping[str, Any]) -> EvidenceIngestResult:
        if body.get("ok") is not True:
            raise ValueError("EvidenceIngestResult.from_response requires ok=true body")
        for key in ("record_hash", "policy_version", "environment"):
            if key not in body:
                raise ValueError(f"missing required field {key!r} in ingest response")
        return cls(
            ok=True,
            record_hash=str(body["record_hash"]),
            policy_version=str(body["policy_version"]),
            environment=str(body["environment"]),
            raw=dict(body),
        )


@dataclass(frozen=True)
class ComplianceSummary:
    """Typed view over ``GET /compliance-summary`` JSON (success or error-shaped).

    When ``ok`` is false, ``verdict`` is ``None``; consult ``error``, ``code``,
    and ``message``. The authoritative lifecycle semantics remain those of the
    hosted service and OpenAPI — this type is a transport projection only.
    """

    ok: bool
    run_id: str
    schema_version: str
    policy_version: str
    verdict: ComplianceVerdict | None
    current_state: Mapping[str, Any] | None
    error: str | None
    code: str | None
    message: str | None
    raw: Mapping[str, Any]

    @classmethod
    def from_response(cls, body: Mapping[str, Any]) -> ComplianceSummary:
        ok = bool(body.get("ok"))
        run_id = str(body.get("run_id", ""))
        schema_version = str(body.get("schema_version", ""))
        policy_version = str(body.get("policy_version", ""))
        verdict: ComplianceVerdict | None = None
        if ok and "verdict" in body:
            v = str(body["verdict"])
            try:
                verdict = ComplianceVerdict(v)
            except ValueError:
                verdict = None
        current_state = body.get("current_state")
        if current_state is not None and not isinstance(current_state, Mapping):
            current_state = None
        err = body.get("error")
        code = body.get("code")
        msg = body.get("message")
        return cls(
            ok=ok,
            run_id=run_id,
            schema_version=schema_version,
            policy_version=policy_version,
            verdict=verdict,
            current_state=current_state if isinstance(current_state, Mapping) else None,
            error=str(err) if err is not None else None,
            code=str(code) if code is not None else None,
            message=str(msg) if msg is not None else None,
            raw=dict(body),
        )
