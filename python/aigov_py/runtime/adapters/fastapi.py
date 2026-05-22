"""FastAPI helpers: FastAPI is imported only when you call these functions."""

from __future__ import annotations

from typing import Any, Callable

from aigov_py.runtime.client import RuntimeGovernanceClient


def install_client_on_app(app: Any, client: RuntimeGovernanceClient) -> None:
    """Attach ``RuntimeGovernanceClient`` to ``app.state.govai_runtime_client``."""
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise TypeError("app must be a fastapi.FastAPI instance")
    app.state.govai_runtime_client = client


def get_runtime_client_from_request(request: Any) -> RuntimeGovernanceClient:
    """Retrieve client from ``request.app.state`` (call inside route or dependency)."""
    from fastapi import Request

    if not isinstance(request, Request):
        raise TypeError("request must be a fastapi.Request instance")
    client = getattr(request.app.state, "govai_runtime_client", None)
    if client is None:
        raise RuntimeError("govai_runtime_client is not set on app.state; call install_client_on_app first")
    return client  # type: ignore[no-any-return]


def make_client_dependency(
    factory: Callable[[], RuntimeGovernanceClient],
) -> Callable[..., RuntimeGovernanceClient]:
    """Build a zero-arg callable suitable for ``Depends(...)`` that builds a fresh client.

    FastAPI is not imported until the returned callable is invoked.
    """

    def _dependency() -> RuntimeGovernanceClient:
        return factory()

    return _dependency
