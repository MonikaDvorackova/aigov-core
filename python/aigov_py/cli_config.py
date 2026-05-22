from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_AUDIT_BASE_URL = "http://127.0.0.1:8088"

CONFIG_ENV = "GOVAI_CONFIG"


def default_config_path() -> Path:
    override = os.environ.get(CONFIG_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path.cwd() / ".govai" / "config.json"


def load_config(path: Path | None = None) -> dict[str, Any]:
    p = path or default_config_path()
    if not p.is_file():
        return {
            "audit_base_url": DEFAULT_AUDIT_BASE_URL,
            "api_key": None,
        }
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"config must be a JSON object: {p}")
    out = {
        "audit_base_url": str(data.get("audit_base_url") or DEFAULT_AUDIT_BASE_URL).rstrip("/"),
        "api_key": data.get("api_key"),
    }
    if out["api_key"] is not None:
        out["api_key"] = str(out["api_key"]).strip() or None
    return out


def save_config(
    *,
    audit_base_url: str,
    api_key: str | None = None,
    path: Path | None = None,
) -> Path:
    p = path.expanduser().resolve() if path else default_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "audit_base_url": audit_base_url.rstrip("/"),
        "api_key": api_key.strip() if isinstance(api_key, str) and api_key.strip() else None,
    }
    with p.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return p


def resolve_audit_base_url(
    *,
    flag: str | None,
    config_path: Path | None = None,
) -> str:
    for env_name in ("GOVAI_AUDIT_BASE_URL", "AIGOV_AUDIT_URL", "AIGOV_AUDIT_ENDPOINT", "GOVAI_BASE_URL"):
        raw = os.environ.get(env_name, "").strip()
        if raw:
            return raw.rstrip("/")
    if flag and flag.strip():
        return flag.strip().rstrip("/")
    cfg = load_config(config_path)
    return str(cfg.get("audit_base_url") or DEFAULT_AUDIT_BASE_URL).rstrip("/")


def resolve_api_key(*, flag: str | None, config_path: Path | None = None) -> str | None:
    raw = os.environ.get("GOVAI_API_KEY", "").strip()
    if raw:
        return raw
    if flag and flag.strip():
        return flag.strip()
    cfg = load_config(config_path)
    key = cfg.get("api_key")
    if isinstance(key, str) and key.strip():
        return key.strip()
    return None
