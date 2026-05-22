from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sigstore.models import Bundle
from sigstore.verify import Verifier
from sigstore.verify.policy import Identity


@dataclass(frozen=True)
class SigstoreIdentity:
    identity: str
    issuer: str


def _verifier_for_env(env: str) -> Verifier:
    e = (env or "").strip().lower()
    if e in ("prod", "production"):
        return Verifier.production()
    if e in ("staging", "stage"):
        return Verifier.staging()
    # Dev: still verify against production by default (deterministic, strict).
    return Verifier.production()


def verify_artifact_with_bundle(
    *,
    artifact_bytes: bytes,
    bundle_json_bytes: bytes,
    identity: SigstoreIdentity,
    sigstore_env: str = "prod",
) -> None:
    """
    Verify an artifact against a Sigstore bundle (hashedrekord).
    Raises on any verification failure (fail-closed).
    """
    bundle = Bundle.from_json(bundle_json_bytes)
    verifier = _verifier_for_env(sigstore_env)
    verifier.verify_artifact(
        artifact_bytes,
        bundle,
        Identity(identity=identity.identity, issuer=identity.issuer),
    )


def verify_dsse_bundle(
    *,
    bundle_json_bytes: bytes,
    identity: SigstoreIdentity,
    sigstore_env: str = "prod",
) -> Tuple[str, bytes]:
    """
    Verify a DSSE bundle and return (payload_type, payload_bytes).
    """
    bundle = Bundle.from_json(bundle_json_bytes)
    verifier = _verifier_for_env(sigstore_env)
    payload_type, payload = verifier.verify_dsse(
        bundle,
        Identity(identity=identity.identity, issuer=identity.issuer),
    )
    return payload_type, payload


def load_bundle_bytes(path: str | Path) -> bytes:
    return Path(path).read_bytes()


def parse_json_payload(payload_bytes: bytes) -> Dict[str, Any]:
    v = json.loads(payload_bytes.decode("utf-8"))
    if not isinstance(v, dict):
        raise ValueError("DSSE payload must be a JSON object")
    return v

