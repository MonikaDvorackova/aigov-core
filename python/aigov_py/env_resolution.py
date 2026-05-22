"""GovAI deployment environment: ``dev`` | ``staging`` | ``prod``.

**Source of truth:** ``docs/env-resolution.md`` at the repository root (kept in sync with
``rust/src/govai_environment.rs``).
"""

from __future__ import annotations

import os

_ENV_KEYS = ("AIGOV_ENVIRONMENT", "AIGOV_ENV", "GOVAI_ENV")


def raw_aigov_environment_from_os() -> str:
    """First non-whitespace value among ``AIGOV_ENVIRONMENT``, ``AIGOV_ENV``, ``GOVAI_ENV``."""
    for key in _ENV_KEYS:
        v = os.environ.get(key)
        if v is not None and v.strip():
            return v
    return ""


def parse_aigov_environment(raw: str) -> str:
    """Trim ``raw``. Empty → ``dev``; otherwise same aliases and errors as Rust ``parse_environment_value``."""
    t = (raw or "").strip()
    if not t:
        return "dev"
    k = t.lower()
    if k in ("dev", "development", "local"):
        return "dev"
    if k in ("staging", "stage"):
        return "staging"
    if k in ("prod", "production"):
        return "prod"
    raise ValueError(
        f"Invalid AIGOV_ENVIRONMENT={raw!r} (expected dev, staging, or prod; see docs/env-resolution.md)"
    )


def resolve_aigov_environment() -> str:
    """Resolve current process tier (for manifests, ingest, CI)."""
    return parse_aigov_environment(raw_aigov_environment_from_os())
