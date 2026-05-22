from __future__ import annotations

import os

import pytest

from aigov_py.env_resolution import (
    parse_aigov_environment,
    raw_aigov_environment_from_os,
    resolve_aigov_environment,
)

_KEYS = ("AIGOV_ENVIRONMENT", "AIGOV_ENV", "GOVAI_ENV")


def _clear() -> None:
    for k in _KEYS:
        os.environ.pop(k, None)


def test_parse_empty_default_dev() -> None:
    assert parse_aigov_environment("") == "dev"
    assert parse_aigov_environment("   ") == "dev"


def test_parse_aliases() -> None:
    assert parse_aigov_environment("DEV") == "dev"
    assert parse_aigov_environment("local") == "dev"
    assert parse_aigov_environment("stage") == "staging"
    assert parse_aigov_environment("production") == "prod"


def test_parse_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid AIGOV_ENVIRONMENT"):
        parse_aigov_environment("qa")


def test_raw_skips_whitespace_only() -> None:
    _clear()
    try:
        os.environ["AIGOV_ENVIRONMENT"] = "   "
        os.environ["AIGOV_ENV"] = "prod"
        assert raw_aigov_environment_from_os() == "prod"
    finally:
        _clear()


def test_raw_precedence() -> None:
    _clear()
    try:
        os.environ["AIGOV_ENVIRONMENT"] = "dev"
        os.environ["GOVAI_ENV"] = "prod"
        assert raw_aigov_environment_from_os() == "dev"
    finally:
        _clear()


def test_resolve_end_to_end() -> None:
    _clear()
    try:
        os.environ["GOVAI_ENV"] = "staging"
        assert resolve_aigov_environment() == "staging"
    finally:
        _clear()
