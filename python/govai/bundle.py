from __future__ import annotations

from typing import Any

from .client import GovAIAPIError, GovAIClient


def get_bundle(client: GovAIClient, run_id: str) -> dict[str, Any]:
    """GET ``/bundle?run_id=...`` — returns the bundle document JSON."""
    data = client.request_json(
        "GET",
        "/bundle",
        params={"run_id": run_id},
        raise_on_body_ok_false=True,
    )
    if not isinstance(data, dict):
        raise TypeError(f"expected dict from /bundle, got {type(data).__name__}")
    return data


def get_bundle_hash(client: GovAIClient, run_id: str) -> str:
    """GET ``/bundle-hash?run_id=...`` — returns the canonical ``bundle_sha256`` hex string."""
    data = client.request_json(
        "GET",
        "/bundle-hash",
        params={"run_id": run_id},
        raise_on_body_ok_false=True,
    )
    if not isinstance(data, dict):
        raise TypeError(f"expected dict from /bundle-hash, got {type(data).__name__}")
    digest = data.get("bundle_sha256")
    if not isinstance(digest, str) or not digest.strip():
        raise GovAIAPIError(
            "bundle_sha256 missing or empty in /bundle-hash response",
            data,
        )
    return digest.strip()
