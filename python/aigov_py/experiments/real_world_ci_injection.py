from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def datasets_path() -> Path:
    return Path(__file__).resolve().parent / "datasets" / "repos.json"


def load_repos() -> list[dict[str, Any]]:
    """Static dataset for ``real_world_ci_runner`` (no network)."""
    raw = datasets_path().read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise TypeError("repos.json must be a JSON array")
    return [x for x in data if isinstance(x, dict)]
