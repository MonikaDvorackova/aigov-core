from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure() -> None:
    """
    Ensure tests import the in-repo Python package, not an installed PyPI build.

    This keeps `python -m pytest -q` deterministic when a different `aigov-py` version is
    installed globally in the active interpreter environment.
    """
    repo_root = Path(__file__).resolve().parents[2]
    python_root = repo_root / "python"
    sys.path.insert(0, str(python_root))
