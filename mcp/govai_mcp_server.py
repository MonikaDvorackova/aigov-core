#!/usr/bin/env python3
"""Deprecated compatibility entrypoint — use ``mcp/aigov_mcp_server.py``."""
from __future__ import annotations

import runpy
import sys
import warnings
from pathlib import Path

warnings.warn(
    "govai_mcp_server.py is deprecated; use aigov_mcp_server.py",
    DeprecationWarning,
    stacklevel=2,
)

if __name__ == "__main__":
    target = Path(__file__).with_name("aigov_mcp_server.py")
    sys.argv[0] = str(target)
    raise SystemExit(runpy.run_path(str(target), run_name="__main__"))
