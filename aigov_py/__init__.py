"""
Repo-local import shim.

This repository's Python package lives under `python/aigov_py/`.
When running from the repo root (e.g. `python -m aigov_py.cli`), we want to
prefer the in-repo sources over any globally installed `aigov_py` package.
"""

from __future__ import annotations

import sys
from pathlib import Path
from pkgutil import extend_path

_ROOT = Path(__file__).resolve().parents[1]
_PYTHON_DIR = _ROOT / "python"

# Ensure `python/` is on sys.path so `import aigov_py.*` can resolve to repo sources.
if str(_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(_PYTHON_DIR))

# Make this a namespace package spanning:
# - repo root `aigov_py/` (this shim)
# - `python/aigov_py/` (real implementation)
__path__ = extend_path(__path__, __name__)

