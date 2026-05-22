"""
Normalize Postgres connection URIs for ``psycopg`` / libpq.

Some stacks (e.g. Node ``pg`` with serverless drivers) append query parameters that are not
valid libpq connection options. ``psycopg`` parses the URI for libpq and rejects unknown keys.
This module strips those while preserving standard options such as ``sslmode``.
"""

from __future__ import annotations

import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Keys known to appear in shared DATABASE_URLs for Node but rejected by libpq/psycopg URI parsing.
# Extend only when a concrete incompatibility is documented.
_PSYCOPG_INCOMPATIBLE_QUERY_KEYS: frozenset[str] = frozenset(
    {
        "statement_cache_capacity",
    }
)


def normalize_postgres_url_for_psycopg(url: str) -> str:
    """
    Return a connection URI safe for ``psycopg.connect(...)``.

    Preserves scheme, credentials, host, port, path, fragment, and all query parameters except
    those listed in ``_PSYCOPG_INCOMPATIBLE_QUERY_KEYS`` (compared case-insensitively).
    ``sslmode`` and other libpq options are kept.
    """
    raw = url.strip()
    if not raw:
        raise ValueError("empty database URL")

    parsed = urlparse(raw)
    if not parsed.query:
        return raw

    kept: list[tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in _PSYCOPG_INCOMPATIBLE_QUERY_KEYS:
            continue
        kept.append((key, value))

    new_query = urlencode(kept, doseq=True)
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
    )


def resolve_psycopg_database_url() -> str:
    """
    Resolve ``GOVAI_DATABASE_URL`` if set, else ``DATABASE_URL``, then normalize for psycopg.

    Raises ``RuntimeError`` if neither variable is set or the result is empty after strip.
    """
    combined = (os.environ.get("GOVAI_DATABASE_URL") or os.environ.get("DATABASE_URL") or "").strip()
    if not combined:
        raise RuntimeError("GOVAI_DATABASE_URL or DATABASE_URL is required for postgres access from Python")
    return normalize_postgres_url_for_psycopg(combined)
