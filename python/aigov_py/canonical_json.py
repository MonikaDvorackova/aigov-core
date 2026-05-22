from __future__ import annotations

import json
from typing import Any


def canonical_dumps(obj: Any) -> str:
    """
    Deterministic JSON:
    - sorted keys
    - no whitespace
    - UTF-8 safe
    """
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_bytes(obj: Any) -> bytes:
    return canonical_dumps(obj).encode("utf-8")
