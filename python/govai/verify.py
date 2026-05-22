from __future__ import annotations

from typing import Any

from .client import GovAIClient


def verify_chain(client: GovAIClient) -> dict[str, Any]:
    """
    GET ``/verify`` — verify append-only audit log hash chain integrity.

    Returns the JSON body (``ok: true`` when the chain is valid, ``ok: false`` with
    ``error`` when it is not). The server responds with HTTP 200 for both outcomes;
    inspect ``ok`` in the returned dict.
    """
    data = client.request_json("GET", "/verify", raise_on_body_ok_false=False)
    if not isinstance(data, dict):
        raise TypeError(f"expected dict from /verify, got {type(data).__name__}")
    return data
